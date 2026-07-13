"""LLM 调用服务：在规则约束下让 LLM 生成表达 / 文案文本。

设计要点：
- 基于 openai SDK（OpenAI 兼容），base_url 可配置 —— GLM（学校代理）/ 通义 /
  豆包 / DeepSeek 通用，换厂家只改环境变量。
- 同步调用，与现有同步 service 风格一致（FastAPI 把同步 handler 丢线程池跑）。
- 失败永不抛：未启用 / 网络 / 超时 / 解析失败统一返回降级状态，
  由调用方决定是否退回 mock_outputs。
- 防御式 JSON 解析：剥 ```json 围栏、抓首个 {...}、json.loads、Pydantic 校验。

返回 (parsed_dict | None, status, used_rule_ids)：
  status ∈ "ok" / "disabled" / "network_error" / "timeout"
         / "parse_error" / "gateway_error"
"""

import json
import logging
import re
from typing import Any

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    NOT_GIVEN,
    OpenAI,
)

from app.config import get_settings
from app.llm_schemas import (
    AssetCopy,
    CrossCulturalExpressionOutputs,
    DomesticExpressionOutputs,
    NaturalLanguageIntent,
)

logger = logging.getLogger("app.llm")

# 用于把 T 映射到"校验后返回 dict"的函数表
_VALIDATORS: dict[type, Any] = {
    DomesticExpressionOutputs: DomesticExpressionOutputs,
    CrossCulturalExpressionOutputs: CrossCulturalExpressionOutputs,
    AssetCopy: AssetCopy,
    NaturalLanguageIntent: NaturalLanguageIntent,
}

# status → 归并到 meta.llm_fallback_reason 的取值
FALLBACK_DISABLED = "disabled"
FALLBACK_NETWORK = "network_error"
FALLBACK_TIMEOUT = "timeout"
FALLBACK_PARSE = "parse_error"
FALLBACK_GATEWAY = "gateway_error"


def _client() -> OpenAI:
    """构造 OpenAI 兼容 client（指向配置的 base_url）。"""
    s = get_settings()
    return OpenAI(
        api_key=s.llm_api_key,
        base_url=s.llm_base_url,
        timeout=s.llm_timeout,
        max_retries=0,  # 不静默延长延迟；失败即降级
    )


def generate(
    *,
    system_prompt: str,
    user_prompt: str,
    output_model: type,
) -> tuple[dict | None, str]:
    """调用 LLM 生成结构化输出并校验。

    Args:
        system_prompt: 系统指令（角色 + 规则 + 输出格式要求）
        user_prompt: 用户输入（茶品上下文 + 具体任务）
        output_model: 用于校验输出的 Pydantic 模型类

    Returns:
        (validated_dict | None, status)。
        成功 → (dict, "ok")；否则 → (None, fallback_reason)。
    """
    s = get_settings()
    if not s.llm_enabled:
        return None, FALLBACK_DISABLED

    try:
        resp = _client().chat.completions.create(
            model=s.llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,  # 低随机但保留多样性（demo 可复现性 vs 缓存另做）
            stream=False,
            response_format=(
                {"type": "json_object"}
                if s.llm_supports_json_mode
                else NOT_GIVEN
            ),
        )
    except APITimeoutError:
        logger.warning("LLM 调用超时 model=%s timeout=%s", s.llm_model, s.llm_timeout)
        return None, FALLBACK_TIMEOUT
    except APIConnectionError as e:
        # 连接层失败（DNS / 握手 / 断流），未拿到网关有效响应。
        # 注意 APITimeoutError 也是 APIConnectionError 子类，必须放它之前，
        # 否则超时会被这里吃掉误归 network_error。
        logger.warning("LLM 连接失败 model=%s err=%s", s.llm_model, e)
        return None, FALLBACK_NETWORK
    except APIStatusError as e:
        # 网关返回了 HTTP 4xx/5xx：内容审查 / 额度耗尽 / 模型不存在 /
        # 上下文超限 / 服务端错误等。区别于连接层 network_error——
        # 这类是请求被处理但被拒绝，前端可据此区分"接错了/被审了" vs "网断了"。
        body = ""
        try:
            body = e.response.text[:500]
        except Exception:
            body = ""
        logger.warning(
            "LLM 网关错误 model=%s status=%s body=%s err=%s",
            s.llm_model, e.status_code, body, e,
        )
        return None, FALLBACK_GATEWAY
    except Exception as e:  # 其他未预期异常，兜底为 network_error
        logger.warning("LLM 调用失败（未分类）model=%s err=%s", s.llm_model, e)
        return None, FALLBACK_NETWORK

    # 代理可能返回非标准 ChatCompletion（如把整个 HTML/JSON 字符串当响应体），
    # SDK 此时不会抛异常，而是直接返回原始字符串——访问 .choices 会 AttributeError。
    # 这里统一兜住，避免把代理形状问题暴露成 500。
    try:
        raw = resp.choices[0].message.content or ""
    except (AttributeError, IndexError, TypeError) as e:
        raw_repr = repr(resp)[:200]
        logger.warning(
            "LLM 响应非标准 ChatCompletion 形状，降级 model=%s type=%s repr=%s err=%s",
            s.llm_model, type(resp).__name__, raw_repr, e,
        )
        return None, FALLBACK_PARSE
    parsed = _extract_json(raw)
    if parsed is None:
        logger.warning("LLM 输出非 JSON，降级 model=%s raw_head=%s", s.llm_model, raw[:200])
        return None, FALLBACK_PARSE

    validator = _VALIDATORS.get(output_model)
    if validator is None:
        logger.warning("未知输出模型 %s，降级", output_model)
        return None, FALLBACK_PARSE

    try:
        obj = validator.model_validate(parsed)
    except Exception as e:
        logger.warning("LLM 输出校验失败，降级 model=%s err=%s", s.llm_model, e)
        return None, FALLBACK_PARSE

    logger.info(
        "LLM 生成成功 model=%s prompt_chars=%d out_fields=%d",
        s.llm_model,
        len(system_prompt) + len(user_prompt),
        len(obj.model_dump()),
    )
    return obj.model_dump(), "ok"


_JSON_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _extract_json(raw: str) -> dict | None:
    """从 LLM 原始输出里剥出首个 JSON 对象。

    先试 ```json 围栏；失败再抓首个 {...} 平衡片段。
    """
    if not raw:
        return None
    m = _JSON_FENCE.search(raw)
    candidate = m.group(1) if m else raw
    try:
        obj = json.loads(candidate)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    # 兜底：抓首个 {...}
    start = candidate.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(candidate)):
        c = candidate[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                try:
                    obj = json.loads(candidate[start : i + 1])
                    if isinstance(obj, dict):
                        return obj
                except json.JSONDecodeError:
                    return None
    return None

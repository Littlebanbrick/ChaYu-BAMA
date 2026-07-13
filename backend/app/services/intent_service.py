"""自然语言意图解析：NL → tea_id + chain。

自然语言入口（POST /api/natural-expression）的专用服务：调一次 LLM，把用户
自由文本解析成结构化意图（识别哪款茶 + 走国内链还是跨文化链），然后由路由层
复用现有 expression_service 生成话术。意图解析只做这两件事，受众 / 风格 /
语气 / 侧重留在原始 NL 里作 directive 原样透传给话术 LLM。

设计要点：
- 茶品枚举从 DB 实时取（data_loader.list_teas），注入 prompt 约束 tea_id 只能
  取清单内 id 之一或 null；新增茶零维护。
- 后端再校验 tea_id ∈ 枚举（防 LLM 幻觉编造 id）、chain ∈ 枚举（防误值），
  不通过则归一为 None / "domestic"。
- intent 结果按 NaturalLanguageIntent 类名 + prompt 单独缓存进 generated_outputs，
  与话术缓存空间隔离；同 NL 二次调用命中缓存即跳过 LLM。
- LLM 未启用 → (None, "disabled")：NL 意图无法 seed 兜底（没有"预置的自然语言
  解析"），由路由层走 fallback。LLM 失败 → status 沿用 llm_service 返回值。
"""

from app import data_loader
from app.config import get_settings
from app.llm_schemas import NaturalLanguageIntent
from app.services import llm_service, output_store, prompts

# chain 合法取值（与 NaturalLanguageIntent.chain Literal 对齐）
_VALID_CHAINS = {"domestic", "cross_cultural"}
# chain 默认值：用户未明确要求英文 / 西方 / 海外时走国内链
_DEFAULT_CHAIN = "domestic"


def parse_intent(text: str) -> tuple[dict | None, str]:
    """解析自然语言意图：识别 tea_id + 判定 chain。

    Args:
        text: 用户原始自然语言输入。

    Returns:
        (intent | None, status)。
        成功 → ({"tea_id": str | None, "chain": "domestic" | "cross_cultural",
                 "intent_llm_generated": bool}, "ok")。
        LLM 未启用 → (None, "disabled")。
        LLM 失败 → (None, <llm_service 的 fallback reason>)。
        intent_llm_generated=True 表示走了 LLM（含缓存命中），False 表示兜底。
    """
    if not get_settings().llm_enabled:
        return None, "disabled"

    tea_list = data_loader.list_teas()
    valid_tea_ids = {t.get("id") for t in tea_list if t.get("id")}

    system_prompt, user_prompt = prompts.build_intent_prompt(tea_list, text)
    input_hash = output_store.compute_input_hash(
        NaturalLanguageIntent, system_prompt, user_prompt
    )

    # 先查缓存：同 NL 二次调用命中即复用，跳过 LLM。
    cached = output_store.get_cached(input_hash)
    if cached is not None:
        return _normalize(cached, valid_tea_ids), "ok"

    llm_out, status = llm_service.generate(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        output_model=NaturalLanguageIntent,
    )
    if llm_out is not None and status == "ok":
        output_store.persist(
            output_type="natural_language_intent",
            tea_id=None,
            route_id=None,
            input_hash=input_hash,
            content=llm_out,
        )
        return _normalize(llm_out, valid_tea_ids), "ok"

    # LLM 失败 / 解析失败 / 网络错误等：NL 意图无法 seed 兜底，交路由层走 fallback。
    return None, status


def _normalize(raw: dict, valid_tea_ids: set[str]) -> dict:
    """对 LLM 输出做后端校验：tea_id 不在枚举内 → None；chain 不合法 → domestic。

    防止 LLM 幻觉编造 id 或回非法 chain 值。intent_llm_generated 标记是否走了
    LLM（含缓存命中），供路由层写入 meta.nl。
    """
    tea_id = raw.get("tea_id")
    if tea_id not in valid_tea_ids:
        tea_id = None

    chain = raw.get("chain")
    if chain not in _VALID_CHAINS:
        chain = _DEFAULT_CHAIN

    return {
        "tea_id": tea_id,
        "chain": chain,
        "intent_llm_generated": True,
    }

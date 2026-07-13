"""表达生成路由（第 3 层）：国内表达 + 跨文化表达 + 自然语言入口。"""

from fastapi import APIRouter

from app import responses
from app.schemas import (
    CrossCulturalExpressionRequest,
    DomesticExpressionRequest,
    NaturalExpressionRequest,
)
from app.services import expression_service, intent_service

router = APIRouter(prefix="/api", tags=["expressions"])


@router.post("/teas/{tea_id}/domestic-expression")
def create_domestic_expression(tea_id: str, body: DomesticExpressionRequest):
    """生成国内中文表达。

    国内表达是跨文化表达横向翻译的源文，属 Demo 主路径，必须预置。
    启用 LLM 时由规则约束生成；未启用 / 失败时退回 seed 预置表达。
    """
    expr, status, llm_meta = expression_service.get_domestic_expression(
        tea_id=tea_id,
        audience=body.audience.model_dump(exclude_none=True),
        style=body.style,
    )
    if status == "tea_not_found":
        return responses.error("TEA_NOT_FOUND", "未找到对应茶品")
    if status == "expression_not_found":
        return responses.fallback_response(
            message="该茶品国内表达 Demo 阶段尚未预置。",
        )

    return responses.success(expr, **_llm_meta_kwargs(llm_meta))


@router.post("/teas/{tea_id}/cross-cultural-expression")
def create_cross_cultural_expression(tea_id: str, body: CrossCulturalExpressionRequest):
    """生成跨文化表达（由国内表达横向翻译派生，关系记于 source_expression_id）。"""
    expr, status, llm_meta = expression_service.get_cross_cultural_expression(
        tea_id=tea_id,
        target_language=body.target_language,
        market=body.market,
        audience_reference=body.audience_reference,
    )

    if status == "tea_not_found":
        return responses.error("TEA_NOT_FOUND", "未找到对应茶品")
    if status in (
        "language_not_supported",
        "market_not_supported",
        "audience_not_supported",
    ):
        # 非开放参数组合 → fallback，不报错
        return responses.fallback_response(
            message="当前目标语言 / 市场 / 受众参照系 Demo 阶段暂未开放。",
            suggested_action="Demo 主路径：铁观音 × 英语 × 欧美市场 × 精品咖啡爱好者。",
        )
    if status == "expression_not_found":
        return responses.fallback_response(
            message="该茶品跨文化表达 Demo 阶段尚未预置。",
        )

    return responses.success(expr, **_llm_meta_kwargs(llm_meta))


@router.post("/natural-expression")
def create_natural_expression(body: NaturalExpressionRequest):
    """自然语言生成表达（NL 入口）。

    用户只输入一段自由文本（如"给第一次喝铁观音的顾客写段亲切简短的三香介绍"），
    后端先调一次意图解析 LLM 识别 tea_id + 判定链路（默认国内链，明确要求英文 /
    西方 / 海外时走跨文化链），再把原始 NL 作为 directive 透传给对应链路的现有
    话术生成逻辑。响应 shape 与对应链路完全一致，前端按 meta.nl.chain 选渲染器。

    - LLM 未启用 → fallback（NL 意图无法 seed 兜底）
    - 意图解析失败 / 识别到的茶不在 DB 枚举 → fallback（不假装识别成功）
    """
    text = (body.text or "").strip()
    if not text:
        return responses.fallback_response(
            message="请输入想要生成的茶品表达描述。",
            suggested_action="例如：给第一次喝铁观音的顾客写段亲切简短的三香介绍。",
        )

    intent, status = intent_service.parse_intent(text)

    if status == "disabled":
        return responses.fallback_response(
            message="自然语言生成需要 LLM 支持，当前未配置 LLM。",
            fallback_reason="feature_not_available",
        )
    if intent is None or intent.get("tea_id") is None:
        return responses.fallback_response(
            message="未能从输入中识别到当前 Demo 支持的茶品。",
            suggested_action="Demo 当前支持：铁观音 / 大红袍 / 金骏眉。"
            "例如：给第一次喝铁观音的顾客写段介绍。",
        )

    tea_id = intent["tea_id"]
    chain = intent["chain"]
    intent_llm_generated = intent.get("intent_llm_generated", False)

    if chain == "cross_cultural":
        # 跨文化链当前仅支持 en / western / specialty_coffee_lovers 唯一组合；
        # directive 承载用户的语气 / 侧重（如"简短"），目标语言始终为英文。
        expr, expr_status, llm_meta = expression_service.get_cross_cultural_expression(
            tea_id=tea_id,
            target_language="en",
            market="western",
            audience_reference="specialty_coffee_lovers",
            directive=text,
        )
        if expr_status in (
            "language_not_supported",
            "market_not_supported",
            "audience_not_supported",
        ):
            return responses.fallback_response(
                message="当前目标语言 / 市场 / 受众参照系 Demo 阶段暂未开放。",
                suggested_action="跨文化链 Demo 主路径：铁观音 × 英语 × 欧美市场 × 精品咖啡爱好者。",
            )
    else:
        expr, expr_status, llm_meta = expression_service.get_domestic_expression(
            tea_id=tea_id,
            audience={},
            style=None,
            directive=text,
        )

    if expr_status == "tea_not_found":
        return responses.error("TEA_NOT_FOUND", "未找到对应茶品")
    if expr_status == "expression_not_found":
        return responses.fallback_response(
            message="该茶品表达 Demo 阶段尚未预置。",
        )
    if expr_status != "ok":
        # 兜底：意图识别成功但话术生成返回未预期状态，按 fallback 处理不白屏。
        return responses.fallback_response(
            message="表达生成暂不可用，请稍后重试。",
        )

    return responses.success(
        expr,
        **_llm_meta_kwargs(llm_meta),
        nl={
            "directive": text,
            "intent_llm_generated": intent_llm_generated,
            "chain": chain,
        },
    )


def _llm_meta_kwargs(llm_meta: dict) -> dict:
    """把 service 返回的 LLM meta 摊成 responses.success 的 extra_meta。

    llm_fallback_reason 仅在非 None（即走了 LLM 但降级）时输出；完全没启用时为 None，
    保持与旧响应一致（不增字段，避免前端困惑）。used_rule_ids 始终输出。
    """
    kwargs: dict = {
        "llm_generated": llm_meta["llm_generated"],
        "used_rule_ids": llm_meta["used_rule_ids"],
    }
    if llm_meta.get("llm_fallback_reason") is not None:
        kwargs["llm_fallback_reason"] = llm_meta["llm_fallback_reason"]
    return kwargs

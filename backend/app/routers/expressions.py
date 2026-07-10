"""表达生成路由（第 3 层）：国内表达 + 跨文化表达。"""

from fastapi import APIRouter

from app import responses
from app.schemas import CrossCulturalExpressionRequest, DomesticExpressionRequest
from app.services import expression_service

router = APIRouter(prefix="/api", tags=["expressions"])


@router.post("/teas/{tea_id}/domestic-expression")
def create_domestic_expression(tea_id: str, body: DomesticExpressionRequest):
    """生成国内中文表达。

    国内表达是跨文化表达横向翻译的源文，属 Demo 主路径，必须预置。
    """
    expr, status = expression_service.get_domestic_expression(
        tea_id=tea_id,
        audience=body.audience.model_dump(exclude_none=True),
        style=body.style,
    )
    if status == "tea_not_found":
        return responses.error("TEA_NOT_FOUND", "未找到对应茶品")

    # 阶段一：_selected_rules 仅用于调试规则筛选，不进接口响应
    expr.pop("_selected_rules", None)
    return responses.success(expr)


@router.post("/teas/{tea_id}/cross-cultural-expression")
def create_cross_cultural_expression(tea_id: str, body: CrossCulturalExpressionRequest):
    """生成跨文化表达（由国内表达横向翻译派生，关系记于 source_expression_id）。"""
    expr, status = expression_service.get_cross_cultural_expression(
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

    expr.pop("_selected_rules", None)
    return responses.success(expr)

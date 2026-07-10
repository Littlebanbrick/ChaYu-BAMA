"""表达生成层（第 3 层）：国内表达 + 跨文化表达，两条同构链路。

国内链与跨文化链地位对等。跨文化表达由国内表达按规则横向翻译派生，
该关系通过 source_expression_id 记录，不进入纵向追溯链。

阶段一：返回 mock_data 中预置的国内/跨文化表达。
规则筛选结果暂以 selected_rules 附在返回里（调试用，非接口字段），
接 LLM 后改为真正注入 prompt 生成。
"""

from app.mock_data import EXPRESSIONS, TEAS
from app.services import rules_service


def get_domestic_expression(
    tea_id: str, audience: dict, style: str | None = None
) -> tuple[dict | None, str]:
    """生成国内中文表达。

    Returns:
        (expression_data, status) — status 为 "ok" / "tea_not_found"。
    """
    if tea_id not in TEAS:
        return None, "tea_not_found"

    expr = EXPRESSIONS["expr_cn_tieguanyin_001"].copy()
    # 用请求里的受众画像覆盖 mock（mock 数据是示例值）
    expr["audience"] = audience
    if style:
        expr["style"] = style

    # 规则筛选：国内链筛选 domestic_expression 规则
    selected = rules_service.select_rules(
        scope="domestic_expression",
        market="domestic",
        audience_reference="domestic_general",
        tea_id=tea_id,
    )
    # 阶段一仅做筛选、暂不接 LLM；selected_rules 不进接口响应（见 router）
    expr["_selected_rules"] = [r["id"] for r in selected]
    return expr, "ok"


def get_cross_cultural_expression(
    tea_id: str,
    target_language: str,
    market: str,
    audience_reference: str,
) -> tuple[dict | None, str]:
    """生成跨文化表达。

    跨文化表达由国内表达横向翻译派生。阶段一直接返回预置 mock，
    其中 source_expression_id 已指向国内表达。

    Returns:
        (expression_data, status) — status 为
        "ok" / "tea_not_found" / "language_not_supported"
        / "market_not_supported" / "audience_not_supported"
    """
    if tea_id not in TEAS:
        return None, "tea_not_found"
    if target_language != "en":
        return None, "language_not_supported"
    if market != "western":
        return None, "market_not_supported"
    if audience_reference != "specialty_coffee_lovers":
        return None, "audience_not_supported"

    expr = EXPRESSIONS["expr_en_tieguanyin_coffee_001"].copy()
    expr["target_language"] = target_language
    expr["market"] = market
    expr["audience_reference"] = audience_reference

    # 规则筛选：跨文化链筛选 cross_cultural_expression 规则
    # （含 rule_domestic_to_foreign_translation 翻译规则 + 观音韵保留规则）
    selected = rules_service.select_rules(
        scope="cross_cultural_expression",
        market=market,
        audience_reference=audience_reference,
        tea_id=tea_id,
    )
    expr["_selected_rules"] = [r["id"] for r in selected]
    return expr, "ok"

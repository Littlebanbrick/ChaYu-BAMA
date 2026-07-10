"""营销物料层（第 4 层）：国内物料 + 跨文化物料，同等重要、相同生成方式。

language=zh → 读取国内表达生成中文物料，source_expression_id 指向国内表达。
language=en → 读取跨文化表达生成英文物料，source_translation_id 指向跨文化表达。
两者均为纵向追溯链上一级；横向翻译关系不在物料层处理。

阶段一：返回 mock_data 中预置物料，不调用真实生图 API
（meta.image_generation_enabled=false）。
"""

from app.mock_data import ASSETS, TEAS
from app.services import rules_service


def get_marketing_asset(
    tea_id: str,
    language: str,
    asset_type: str = "poster",
    platform: str | None = None,
    route_id: str | None = None,
    style: str | None = None,
) -> tuple[dict | None, str]:
    """生成营销物料。

    Returns:
        (asset_data, status) — status 为
        "ok" / "tea_not_found" / "language_not_supported"
    """
    if tea_id not in TEAS:
        return None, "tea_not_found"
    if language not in ("zh", "en"):
        return None, "language_not_supported"

    asset_key = "asset_tieguanyin_poster_zh_001" if language == "zh" else "asset_tieguanyin_poster_en_001"
    asset = ASSETS[asset_key].copy()
    if platform:
        asset["platform"] = platform
    if route_id:
        asset["route_id"] = route_id
    if style:
        asset["style"] = style

    # 规则筛选：物料层筛选 marketing_asset 规则（如事实边界）
    selected = rules_service.select_rules(
        scope="marketing_asset",
        market="domestic" if language == "zh" else "western",
        audience_reference="domestic_general" if language == "zh" else "specialty_coffee_lovers",
        tea_id=tea_id,
    )
    asset["_selected_rules"] = [r["id"] for r in selected]
    return asset, "ok"

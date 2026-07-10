"""营销物料路由（第 4 层）。"""

from fastapi import APIRouter

from app import responses
from app.schemas import MarketingAssetRequest
from app.services import asset_service

router = APIRouter(prefix="/api", tags=["assets"])


@router.post("/teas/{tea_id}/marketing-asset")
def create_marketing_asset(tea_id: str, body: MarketingAssetRequest):
    """生成图片物料数据（海报文案 + 雷达图 + image_prompt）。

    language=zh → 国内物料（source_expression_id 指向国内表达）
    language=en → 跨文化物料（source_translation_id 指向跨文化表达）
    """
    asset, status = asset_service.get_marketing_asset(
        tea_id=tea_id,
        language=body.language,
        asset_type=body.asset_type,
        platform=body.platform,
        route_id=body.route_id,
        style=body.style,
    )

    if status == "tea_not_found":
        return responses.error("TEA_NOT_FOUND", "未找到对应茶品")
    if status == "language_not_supported":
        return responses.fallback_response(
            message="当前语言 Demo 阶段暂未开放，仅支持 zh / en。",
        )

    asset.pop("_selected_rules", None)
    return responses.success(
        asset,
        image_generation_enabled=False,  # 当前未真正调用生图服务
    )

"""营销物料路由（第 4 层）。"""

from fastapi import APIRouter

from app import enum_map, responses
from app.schemas import MarketingAssetRequest
from app.services import asset_service
from app.routers.expressions import _llm_meta_kwargs

router = APIRouter(prefix="/api", tags=["assets"])


@router.post("/teas/{tea_id}/marketing-asset")
def create_marketing_asset(tea_id: str, body: MarketingAssetRequest):
    """生成图片物料数据（海报文案 + 雷达图 + image_prompt）。

    language=zh → 国内物料（source_expression_id 指向国内表达）
    language=en → 跨文化物料（source_translation_id 指向跨文化表达）

    启用 LLM 时由规则约束生成 copy + image_prompt；雷达数值仍由 seed
    事实提供。物料接口本身不调生图（image_generation_enabled=false），
    真实出图走独立接口 POST /api/image/generate（豆包 Seedream，图内渲染中文知识文字）。

    platform / style：前端可传中文枚举（小红书/国风等），此处按 app.enum_map
    翻成内部英文值后再交给 service——service / prompt / 缓存键 / 响应回显
    统一只认英文值，映射集中在 enum_map 一处。
    """
    asset, status, llm_meta = asset_service.get_marketing_asset(
        tea_id=tea_id,
        language=body.language,
        asset_type=body.asset_type,
        platform=enum_map.resolve_platform(body.platform),
        route_id=body.route_id,
        style=enum_map.resolve_marketing_style(body.style),
        content_theme=enum_map.resolve_content_theme(body.content_theme),
    )

    if status == "tea_not_found":
        return responses.error("TEA_NOT_FOUND", "未找到对应茶品")
    if status == "language_not_supported":
        return responses.fallback_response(
            message="当前语言 Demo 阶段暂未开放，仅支持 zh / en。",
        )
    if status == "asset_not_found":
        return responses.fallback_response(
            message="该茶品对应语言物料 Demo 阶段尚未预置。",
        )

    return responses.success(
        asset,
        image_generation_enabled=False,  # 当前未真正调用生图服务
        **_llm_meta_kwargs(llm_meta),
    )

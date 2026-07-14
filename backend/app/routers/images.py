"""生图路由：POST /api/image/generate（豆包 Seedream）。

两步联调：前端先调 marketing-asset 拿 image_prompt，再传 prompt 调本接口出图。
图内渲染中文知识文字：tea_id + language 都传时，后端从 seed asset 表取 copy
（headline/subheadline/body），交给 service 印进图；不传则纯画面出图。
"""

from fastapi import APIRouter

from app import data_loader, responses
from app.schemas import ImageGenerateRequest
from app.services import image_service

router = APIRouter(prefix="/api", tags=["images"])


@router.post("/image/generate")
def generate_image(body: ImageGenerateRequest):
    """生成图片（豆包 Seedream）。

    前端先调 marketing-asset 拿 image_prompt，再把该 prompt 传给本接口出图。
    传 tea_id + language 时，后端按 tea_id + language 从 seed asset 表取 copy
    （headline/subheadline/body）印进图——海报把知识点 + 产品文案直接渲染在图上。
    取不到 copy（未配 / asset 不存在）→ copy=None，纯画面出图（不抛、不 fallback）。
    未配置 IMAGE_* / 调用失败 → fallback（生图无 seed 兜底，区别于文本三接口）。
    成功返回 Ark 临时图片链接（30 天有效）。
    """
    copy = None
    if body.tea_id and body.language:
        asset = data_loader.get_asset_by_language(body.tea_id, body.language)
        if asset:
            copy = asset.get("copy")

    result, status = image_service.generate_image(
        prompt=body.prompt, size=body.size, style=body.style,
        scene=body.scene, copy=copy, language=body.language,
    )
    if result is None:
        if status == "disabled":
            return responses.fallback_response(
                title="生图未启用",
                message=(
                    "未配置 IMAGE_API_KEY / IMAGE_BASE_URL，生图不可用。"
                    "请在 backend/.env 填豆包 Seedream（火山方舟 Ark）凭证后重启。"
                ),
                fallback_reason="image_not_enabled",
            )
        return responses.fallback_response(
            title="生图失败",
            message=f"生图调用失败（{status}），Demo 阶段暂不提供真实图片。",
            fallback_reason=status,
        )

    data = {
        "image_url": result["url"],
        "prompt": body.prompt,
        "model": result["model"],
        "size": result["size"],
        "style": result["style"],
        "scene": result["scene"],
        "language": result["language"],
    }
    if body.tea_id:
        data["tea_id"] = body.tea_id
    if body.route_id:
        data["route_id"] = body.route_id
    return responses.success(data, image_generated=True)

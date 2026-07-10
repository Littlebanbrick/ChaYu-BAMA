"""Fallback 路由。

P1：GET/POST /api/fallback —— 显式 fallback 入口。
P2：占位接口（video-asset / translate / image/generate / audio/generate
     / markets / audience-references）统一返回 fallback，避免 404。
"""

from fastapi import APIRouter, Request

from app import responses
from app.schemas import FallbackRequest

router = APIRouter(prefix="/api", tags=["fallback"])


@router.get("/fallback")
def get_fallback():
    """显式 fallback 入口（P1）。"""
    return responses.fallback_response()


@router.post("/fallback")
def post_fallback(body: FallbackRequest):
    """前端访问未开放功能时的统一占位（P1）。"""
    return responses.fallback_response(
        message=f"功能 {body.feature or '未知'} 已在产品规划中，Demo 阶段暂不提供。"
        if body.feature
        else "该能力已在产品规划中，Demo 阶段暂不提供真实生成结果。"
    )


# ---------------------------------------------------------------------------
# P2 占位接口：注册路由 + 返回 fallback，不实现真实逻辑
# ---------------------------------------------------------------------------


@router.post("/teas/{tea_id}/video-asset")
def video_asset(tea_id: str):
    """视频生成（P2 占位）。"""
    return responses.fallback_response(message="视频生成 Demo 阶段暂不开放。")


@router.post("/translate")
def translate():
    """通用翻译（P2 占位）。"""
    return responses.fallback_response(message="通用翻译 Demo 阶段暂不开放，跨文化表达请走 cross-cultural-expression。")


@router.post("/image/generate")
def image_generate():
    """真实生图（P2 占位）。"""
    return responses.fallback_response(message="真实生图 Demo 阶段暂不开放，marketing-asset 返回 image_prompt 供前端渲染。")


@router.post("/audio/generate")
def audio_generate():
    """音频生成（P2 占位）。"""
    return responses.fallback_response(message="音频生成 Demo 阶段暂不开放。")


@router.get("/markets")
def markets():
    """市场列表（P2 占位）。"""
    return responses.fallback_response(message="市场列表 Demo 阶段暂以 demo-routes 暴露。")


@router.get("/audience-references")
def audience_references():
    """受众参照系列表（P2 占位）。"""
    return responses.fallback_response(message="受众参照系列表 Demo 阶段暂以 demo-routes 暴露。")


# ---------------------------------------------------------------------------
# 全局 /api/* 404 fallback：未知 API 路由不返回默认 404，返回 fallback JSON
# ---------------------------------------------------------------------------


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
def catch_all_api(path: str, request: Request):
    """捕获所有未匹配的 /api/* 请求，返回 fallback（fallback_reason=api_not_implemented）。"""
    return responses.fallback_response(
        title="接口暂未开放",
        message="该接口尚未在 Demo 后端中实现。请确认是否属于后续功能。",
        fallback_reason="api_not_implemented",
    )

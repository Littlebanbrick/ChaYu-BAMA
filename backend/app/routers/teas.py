"""Demo 路径 + 茶品 + 知识卡片 + 风味坐标路由（第 1、2 层 + demo-routes）。"""

from fastapi import APIRouter

from app import responses
from app.mock_data import DEMO_ROUTES, FLAVOR_PROFILES, KNOWLEDGE, TEAS

router = APIRouter(prefix="/api", tags=["teas"])


@router.get("/demo-routes")
def list_demo_routes():
    """获取当前支持的 Demo 路径（国内链 + 跨文化链）。"""
    return responses.success(DEMO_ROUTES)


@router.get("/teas")
def list_teas():
    """获取茶品列表。"""
    return responses.success(list(TEAS.values()))


@router.get("/teas/{tea_id}/knowledge")
def get_knowledge(tea_id: str):
    """获取茶品知识卡片（第 1 层：知识 / 证据层）。"""
    knowledge = KNOWLEDGE.get(tea_id)
    if knowledge is None:
        return responses.error("TEA_NOT_FOUND", "未找到对应茶品")
    return responses.success(knowledge)


@router.get("/teas/{tea_id}/flavor-profile")
def get_flavor_profile(tea_id: str):
    """获取风味坐标卡（第 2 层：风味结构化层）。"""
    profile = FLAVOR_PROFILES.get(tea_id)
    if profile is None:
        return responses.error("TEA_NOT_FOUND", "未找到对应茶品")
    return responses.success(profile)

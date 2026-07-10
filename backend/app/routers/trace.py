"""追溯路由。"""

from fastapi import APIRouter

from app import responses
from app.services import trace_service

router = APIRouter(prefix="/api", tags=["trace"])


@router.get("/trace/{output_id}")
def get_trace(output_id: str):
    """查询某个输出的纵向追溯链（四层，国内链 / 跨文化链各自对称）。"""
    trace = trace_service.build_trace(output_id)
    if trace is None:
        return responses.error("TRACE_NOT_FOUND", "未找到对应追溯链")
    return responses.success(trace)

"""FastAPI 入口。

阶段一（静态可跑）：内存 mock + 规则筛选骨架 + 全套 P0 接口 + fallback。
启动：
    cd backend
    uvicorn app.main:app --reload
    # 或直接：python app/main.py
Swagger: http://localhost:8000/docs
"""

# 让 `python app/main.py` 也能找到 `app` 包（把 backend/ 加入搜索路径）。
# 必须在 import app.* 之前执行。uvicorn 方式不受影响。
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import assets, expressions, fallback, teas, trace

app = FastAPI(
    title="中国茶 AI 表达 Demo",
    description=(
        "中国茶感知与文化表达的分层翻译系统 Demo。"
        "主路径：1 款茶（铁观音）× 图片物料 ×（国内链 + 跨文化链）两条同构链路。"
    ),
    version="0.1.0",
)

# Demo 阶段放开 CORS，方便前端本地联调；上线前应收紧 origins。
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    """根路径：给个入口提示，非业务接口。"""
    return {
        "name": "中国茶 AI 表达 Demo",
        "docs": "/docs",
        "main_routes": [
            "/api/demo-routes",
            "/api/teas",
            "/api/teas/{tea_id}/knowledge",
            "/api/teas/{tea_id}/flavor-profile",
            "/api/teas/{tea_id}/domestic-expression",
            "/api/teas/{tea_id}/cross-cultural-expression",
            "/api/teas/{tea_id}/marketing-asset",
            "/api/trace/{output_id}",
        ],
    }


@app.get("/health")
def health():
    """健康检查。"""
    return {"status": "ok"}


# 挂载业务路由（顺序重要：具体路由须在 fallback 的 catch-all 之前注册，
# 否则 /api/{path:path} 会抢先匹配 /api/teas 等）。
app.include_router(teas.router)
app.include_router(expressions.router)
app.include_router(assets.router)
app.include_router(trace.router)
app.include_router(fallback.router)  # 含 P1/P2 占位 + /api/* 全局 catch-all


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)

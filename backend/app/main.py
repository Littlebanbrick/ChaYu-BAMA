"""FastAPI 入口。

运行时读路径已切库：data_loader getter 查 backend/data/tea.db（由
seed.py --reset 灌表）；写路径经 output_store 查/写 generated_outputs 表。
未灌表时启动打印警告，读路径返回空/404 不白屏。LLM 已接入（可选，
未配置 key 或失败时透明退回 seed 兜底）。真实生图已接入（image_service，
豆包 Seedream，未配置/失败走 fallback，无 seed 兜底，图内渲染中文知识文字）；视频生成仍走 fallback。

启动：
    cd backend
    python scripts/seed.py --reset   # 灌表（fresh clone 必跑一次）
    uvicorn app.main:app --reload
    # 或直接：python app/main.py
Swagger: http://localhost:8000/docs
"""

# 让 `python app/main.py` 也能找到 `app` 包（把 backend/ 加入搜索路径）。
# 必须在 import app.* 之前执行。uvicorn 方式不受影响。
import sys
from contextlib import asynccontextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import data_loader  # noqa: F401  lifespan 启动时检查 DB 灌表状态
from app import responses
from app.config import get_settings
from app.routers import assets, debug, expressions, fallback, images, teas, trace


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时检查 DB 灌表状态 + 打印一次 LLM 启用状态（不输出 key）。

    读路径已切库：运行时 getter 查 backend/data/tea.db（由 seed.py --reset 灌表）。
    若库未灌（表缺失或 teas 表为空），打印醒目警告，不 crash 也不自动灌——
    显式由开发者运行 `python scripts/seed.py --reset`（与 runbook 一致）。
    未灌表时读路径返回空/404，由响应本身暴露，不白屏。
    """
    _check_seeded()
    s = get_settings()
    if s.llm_enabled:
        print(f"[startup] LLM 已启用：model={s.llm_model} timeout={s.llm_timeout}")
    else:
        print("[startup] LLM 未启用（未配置 LLM_API_KEY / LLM_BASE_URL），生成接口走 mock 兜底")
    yield


def _check_seeded() -> None:
    """检查 tea.db 是否已灌表：teas 表存在且有行。否则打印警告。best-effort。

    警告文本用 ASCII 标记（[WARNING]），不用 emoji——Windows GBK/cp936 控制台
    无法编码 ⚠ 等 emoji，会让 print 抛 UnicodeEncodeError 掩盖真正的检查结果。
    """
    try:
        from sqlalchemy import inspect, select

        from app.database import make_session
        from app.models import Tea

        engine = data_loader._current_read_engine()
        if not inspect(engine).has_table("teas"):
            print("[startup] [WARNING] 数据库未灌表（teas 表不存在）。请运行：python scripts/seed.py --reset")
            return
        with make_session(engine) as s:
            n = s.execute(select(Tea)).all()
        if not n:
            print("[startup] [WARNING] 数据库 teas 表为空。请运行：python scripts/seed.py --reset")
            return
        print(f"[startup] 数据库已就绪：{len(n)} 款茶已灌表")
    except Exception as e:
        print(f"[startup] [WARNING] 数据库检查失败（读路径可能不可用）：{e}")


app = FastAPI(
    title="中国茶 AI 表达 Demo",
    description=(
        "中国茶感知与文化表达的分层翻译系统 Demo。"
        "主路径：1 款茶（铁观音）× 图片物料 ×（国内链 + 跨文化链）两条同构链路。"
    ),
    version="0.3.0",
    lifespan=lifespan,
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


@app.exception_handler(RequestValidationError)
async def _validation_exception_handler(request: Request, exc: RequestValidationError):
    """请求体校验失败统一走 error 响应格式，前端解析一致。

    FastAPI 默认返回 {"detail": [...]}，这里改造成本项目的
    { success: false, error: {code, message} } 结构。
    """
    first = exc.errors()[0] if exc.errors() else {}
    loc = ".".join(str(x) for x in first.get("loc", []))
    message = first.get("msg", "请求参数校验失败")
    detail = f"{loc}: {message}" if loc else message
    return JSONResponse(
        status_code=422,
        content=responses.error("VALIDATION_ERROR", detail),
    )


# 挂载业务路由（顺序重要：具体路由须在 fallback 的 catch-all 之前注册，
# 否则 /api/{path:path} 会抢先匹配 /api/teas 等）。
app.include_router(teas.router)
app.include_router(expressions.router)
app.include_router(assets.router)
app.include_router(images.router)
app.include_router(trace.router)
app.include_router(debug.router)  # /api/health-llm（调试用，非 P0 契约）
app.include_router(fallback.router)  # 含 P1/P2 占位 + /api/* 全局 catch-all


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)

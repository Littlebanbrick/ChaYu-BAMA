"""pytest 全局夹具。

LLM 禁用策略：直接 monkeypatch 每个模块里 `get_settings` 的名字绑定。
为什么不用 app.dependency_overrides：各 service / router / llm_service 里都是
`get_settings()` 直接函数调用（不是 Depends(get_settings)），DI 覆盖拦不住，
真 .env（gitignored，含真实 key）会让 llm_enabled=True 并真调 LLM。
而 `from app.config import get_settings` 在导入时已把函数对象绑到各模块命名空间，
所以必须逐个 patch 每个引用模块的 get_settings 属性。

测试默认全程 LLM disabled → 走 seed 兜底（与未接 LLM 行为一致）。
test_llm_fallback.py 用局部 fixture 覆盖此默认，单独验证降级契约。
显式传参构造 Settings(llm_api_key="", ...) 会覆盖 .env 读取（pydantic-settings v2
init 参数优先级高于文件/环境），干净绕开真实 key。
"""

import importlib
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import config, data_loader
from app.config import Settings
from app.main import app
from app.services import output_store
from scripts.seed import run_seed

# 所有直接 `from app.config import get_settings` 后在运行时调用 get_settings() 的模块。
# 改 app.config.get_settings 不影响它们持有的导入期引用，须逐模块 patch。
_SETTINGS_MODULES = (
    "app.services.expression_service",
    "app.services.asset_service",
    "app.services.intent_service",
    "app.services.llm_service",
    "app.routers.debug",
    "app.main",
)

_DISABLED_SETTINGS = Settings(llm_api_key="", llm_base_url="")


def _patch_get_settings(monkeypatch, settings: Settings) -> None:
    """把各模块的 get_settings 名字替换成返回指定 settings 的 lambda。"""
    fn = lambda s=settings: s  # noqa: E731  闭包捕获 settings
    for mod_name in _SETTINGS_MODULES:
        mod = importlib.import_module(mod_name)
        monkeypatch.setattr(mod, "get_settings", fn, raising=False)
    monkeypatch.setattr(config, "get_settings", fn, raising=False)


@pytest.fixture(autouse=True)
def llm_disabled(monkeypatch) -> Iterator[None]:
    """默认禁用 LLM：各模块 get_settings 返回未启用配置。

    autouse=True → 所有测试默认生效；test_llm_fallback.py 用局部 fixture 覆盖。
    """
    _patch_get_settings(monkeypatch, _DISABLED_SETTINGS)
    yield


@pytest.fixture(autouse=True)
def _isolated_output_db(tmp_path) -> Iterator[None]:
    """把 output_store 的 generated_outputs 重定向到临时库，隔离真实 tea.db。

    autouse=True：每个测试都用独立临时 DB，且 teardown dispose 释放文件锁。
    否则 test_llm_fallback（LLM enabled 但失败）虽不写缓存，但若将来有
    测试触发 persist，会在仓库内生成 stray tea.db。
    """
    output_store.set_test_db_path(tmp_path / "test_outputs.db")
    yield
    output_store.reset_engine()


@pytest.fixture(scope="session", autouse=True)
def _seeded_read_db(tmp_path_factory) -> Iterator[None]:
    """session 级：灌一份临时 tea.db，把 data_loader 读 engine 指向它。

    读路径已切库：getter 查 SQLite。测试需要一个已灌表的库——在 tmp_path_factory
    里 run_seed(reset=True) 灌一次（不污染真实 backend/data/tea.db），session 内
    所有读测试共享。读测试对 seed 表只读不写，共享安全。

    与 output_store 的 _isolated_output_db（per-test）正交：seed.py 不灌
    generated_outputs 表，读测试也不碰它。test_seed_db.py 用自己的 tmp_path +
    run_seed（不经共享 engine），不受影响。
    """
    db_path = tmp_path_factory.mktemp("seeded_read_db") / "tea.db"
    run_seed(reset=True, db_path=db_path, verbose=False)
    data_loader.set_read_db_path(db_path)
    yield
    data_loader.reset_read_engine()


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    """FastAPI TestClient，与 uvicorn 同一 app 对象。"""
    with TestClient(app) as c:
        yield c


# 供测试复用
TEA_ID = "BAMA_SZZ_TGY_NX"

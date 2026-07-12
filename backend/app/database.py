"""SQLAlchemy engine + Base + DB 路径。

最小运行时（阶段二第一步）：仅供 scripts/seed.py 和 tests 使用。运行时
（main.py）仍走内存 data_loader，不查 DB —— 本模块在 main.py 启动路径上
不被 import，不产生任何运行时开销。

DB 路径硬编码 backend/data/tea.db（与 data_loader.SEEDS_DIR 同款写法），
已被 .gitignore 覆盖。多环境配置等真需要时再加 config 项。
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# backend/app/database.py → backend/data/tea.db
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "tea.db"


def make_engine(db_path: Path | None = None) -> Engine:
    """构造同步 sqlite engine。

    db_path 默认指向 backend/data/tea.db；测试可传入临时路径，不污染真实库。
    路径用 as_posix() 转正斜杠，避免 Windows 反斜杠在 sqlite URL 里出错。
    """
    path = db_path or DB_PATH
    url = f"sqlite:///{path.as_posix()}"
    return create_engine(url, echo=False, future=True)


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。models.py 里的表都继承它。"""


def make_session(engine: Engine):
    """构造绑定到指定 engine 的 sessionmaker（调用方负责 close）。"""
    return sessionmaker(bind=engine, future=True)()

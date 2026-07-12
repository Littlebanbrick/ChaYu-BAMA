"""seed.py — 把 YAML seed 灌进 SQLite（阶段二最小运行时）。

阶段一不使用 SQLite：seed 文件即数据源，由 app.data_loader 直接加载到内存。
阶段二最小运行时（本脚本）：运行 `python scripts/seed.py --reset` 即可把
全部 seed 灌进 backend/data/tea.db，作为可复现的 DB 产物验证 schema 正确性。

边界：
- 运行时（main.py）仍走内存 data_loader，不查 DB；本脚本只产 DB，不切换运行时。
- 嵌套结构用 JSON 列，不为子结构建关系表。
- 幂等：--reset 每次删旧库重建。
- 数据源与运行时同一份：复用 data_loader.all_seeds() 读 YAML，避免重复读取逻辑。

用法：
    python scripts/seed.py --reset
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# 让 `python scripts/seed.py` 也能找到 `app` 包（把 backend/ 加入搜索路径）。
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import inspect, select
from sqlalchemy.engine import Engine

from app import data_loader, models  # noqa: E402  须在 sys.path 调整后
from app.database import Base, DB_PATH, make_engine, make_session  # noqa: E402

# seed 顶层键 → ORM 模型 的灌表顺序（按 FK 依赖：被引用的表先灌）。
# tea_terms 是 dict（非 list），单独在 _seed_tea_terms 里展开。
_SEED_PLAN: list[tuple[str, type[Base]]] = [
    ("teas", models.Tea),
    ("evidence_sources", models.EvidenceSource),
    ("tea_knowledge", models.TeaKnowledge),
    ("flavor_profiles", models.FlavorProfile),
    ("demo_routes", models.DemoRoute),
    ("rules", models.GenerationRule),  # seed 顶层键是 rules，表名 generation_rules
    ("cross_cultural_terms", models.CrossCulturalTerm),
    ("expression_strategies", models.ExpressionStrategy),
    ("expressions", models.Expression),
    ("assets", models.Asset),
    ("trace_nodes", models.TraceLink),  # seed 顶层键是 trace_nodes，表名 trace_links
]

# ORM 模型 → seed 顶层键（用于行数校验；tea_terms 单独处理）。
_MODEL_TO_SEED_KEY = {
    models.Tea: "teas",
    models.EvidenceSource: "evidence_sources",
    models.TeaKnowledge: "tea_knowledge",
    models.FlavorProfile: "flavor_profiles",
    models.DemoRoute: "demo_routes",
    models.GenerationRule: "rules",
    models.CrossCulturalTerm: "cross_cultural_terms",
    models.ExpressionStrategy: "expression_strategies",
    models.Expression: "expressions",
    models.Asset: "assets",
    models.TraceLink: "trace_nodes",
}


def run_seed(
    reset: bool = True,
    db_path: Path | None = None,
    verbose: bool = True,
) -> dict[str, int]:
    """从 YAML seed 灌进 SQLite，返回 {表名: 行数}。

    reset=True 时先删旧库再建；否则在现有库上追加灌（最小运行时一律用 reset）。
    db_path 默认 backend/data/tea.db；测试可传临时路径，不污染真实库。
    """
    if not reset:
        raise ValueError("当前最小运行时仅支持 --reset（删库重建）；增量灌表待后续阶段。")

    path = db_path or DB_PATH
    # 删旧库（含 -journal/-wal/-shm 残留），保证幂等。
    for suffix in ("", "-journal", "-wal", "-shm"):
        p = path.with_name(path.name + suffix) if suffix else path
        if p.exists():
            os.remove(p)

    seeds = data_loader.all_seeds()
    counts: dict[str, int] = {}

    engine = make_engine(path)
    try:
        Base.metadata.create_all(engine)
        with make_session(engine) as session:
            for seed_key, model in _SEED_PLAN:
                rows = seeds.get(seed_key, [])
                objs = [model(**_coerce_row(model, row)) for row in rows]
                session.add_all(objs)
                session.commit()
                counts[model.__tablename__] = len(objs)

            # tea_terms 是 dict（tea_id → [term...]），展开成多行。
            tea_terms = seeds.get("tea_terms", {})
            term_objs = [
                models.TeaTerm(tea_id=tea_id, term=term)
                for tea_id, terms in tea_terms.items()
                for term in (terms or [])
            ]
            session.add_all(term_objs)
            session.commit()
            counts["tea_terms"] = len(term_objs)
    finally:
        # 释放 engine 连接：Windows 下不 dispose 会占用 db 文件，
        # 导致同进程复跑（如 test_idempotent_reseed）删旧库时 PermissionError。
        engine.dispose()

    # generated_outputs 仅建空表占位，不灌数据。
    counts["generated_outputs"] = 0

    _verify_row_counts(path, counts)
    if verbose:
        _print_summary(path, counts)
    return counts


def _coerce_row(model: type[Base], row: dict) -> dict:
    """把 seed 行 dict 过滤成该模型已声明的列（丢弃 seed 多余字段）。

    seed 各茶字段不齐（如 shelf_life 仅牛一有），但 ORM 列已 nullable，
    直接传多余/缺失字段都安全；这里只过滤掉模型没有的列，避免 SQLAlchemy
    报"unexpected column"。
    """
    declared = {c.name for c in model.__table__.columns}
    return {k: v for k, v in row.items() if k in declared}


def _verify_row_counts(db_path: Path, counts: dict[str, int]) -> None:
    """灌完后查每张表行数，与 seed list 长度比对，不一致则抛错。

    tea_terms 展开行数单独算；generated_outputs 恒 0。
    用独立 engine + dispose，避免连接占用 db 影响后续操作。
    """
    seeds = data_loader.all_seeds()
    engine = make_engine(db_path)
    insp = inspect(engine)
    mismatches: list[str] = []
    try:
        for model, seed_key in _MODEL_TO_SEED_KEY.items():
            table = model.__tablename__
            if not insp.has_table(table):
                mismatches.append(f"{table}: 表不存在")
                continue
            with make_session(engine) as s:
                db_count = len(s.execute(select(model)).all())
            seed_count = len(seeds.get(seed_key, []))
            if db_count != seed_count:
                mismatches.append(
                    f"{table}: DB={db_count} 但 seed={seed_count}"
                )

        # tea_terms：展开行数应等于各茶术语列表长度之和。
        with make_session(engine) as s:
            db_term_count = len(s.execute(select(models.TeaTerm)).all())
        seed_term_count = sum(len(v) for v in seeds.get("tea_terms", {}).values())
        if db_term_count != seed_term_count:
            mismatches.append(
                f"tea_terms: DB={db_term_count} 但 seed展开={seed_term_count}"
            )
    finally:
        engine.dispose()

    if mismatches:
        raise RuntimeError(
            "seed.py 行数校验失败：\n  " + "\n  ".join(mismatches)
        )


def _print_summary(path: Path, counts: dict[str, int]) -> None:
    print(f"[seed.py] 已生成 DB：{path}")
    print("[seed.py] 各表行数：")
    for table, n in counts.items():
        print(f"  {table:25s} {n}")
    total = sum(counts.values())
    print(f"  {'（合计）':25s} {total}")


def main() -> None:
    parser = argparse.ArgumentParser(description="把 YAML seed 灌进 SQLite（阶段二启用）")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="重建数据库后重新导入全部 seed 数据（当前唯一支持模式）",
    )
    args = parser.parse_args()

    if not args.reset:
        parser.print_help()
        print(
            "\n提示：当前最小运行时仅支持 --reset（删库重建）。"
            "运行 `python scripts/seed.py --reset` 生成 backend/data/tea.db。"
        )
        return

    run_seed(reset=True)


if __name__ == "__main__":
    main()

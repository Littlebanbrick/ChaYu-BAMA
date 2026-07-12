"""seed.py --reset 生成的 tea.db 的 schema 与行数校验。

验证阶段二最小运行时：从 YAML seed 灌库后，库结构正确、数据完整、幂等。
不依赖 LLM（conftest 的 autouse fixture 无害 —— seed.py 不读 settings）。
"""

from pathlib import Path

import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.engine import Engine

from app import data_loader, models
from app.database import make_engine, make_session
from scripts.seed import run_seed

# 期望存在的表（含 generated_outputs 占位空表）。
EXPECTED_TABLES = {
    "teas",
    "evidence_sources",
    "tea_knowledge",
    "flavor_profiles",
    "demo_routes",
    "generation_rules",
    "cross_cultural_terms",
    "expression_strategies",
    "expressions",
    "assets",
    "trace_links",
    "tea_terms",
    "generated_outputs",
}

# 三款茶必须在库（铁观音以新 ID BAMA_SZZ_TGY_NX 为准）。
EXPECTED_TEA_IDS = {
    "BAMA_SZZ_TGY_NX",
    "BAMA_NY_WRT_DHP",
    "BAMA_DH_BT_JJM",
}


@pytest.fixture
def seeded_engine(tmp_path):
    """在临时路径灌一份 DB，不污染真实 backend/data/tea.db。

    用完 dispose 释放连接（Windows 下不 dispose 会占用 db 文件）。
    返回的是已 dispose 前的 engine；调用方用完不必再 dispose。
    """
    db_path: Path = tmp_path / "tea.db"
    run_seed(reset=True, db_path=db_path, verbose=False)
    engine = make_engine(db_path)
    yield engine
    engine.dispose()


def test_db_file_created(tmp_path):
    db_path = tmp_path / "tea.db"
    assert not db_path.exists()
    run_seed(reset=True, db_path=db_path, verbose=False)
    assert db_path.exists()
    assert db_path.stat().st_size > 0


def test_all_tables_exist(seeded_engine):
    insp = inspect(seeded_engine)
    tables = set(insp.get_table_names())
    missing = EXPECTED_TABLES - tables
    assert not missing, f"缺表：{missing}"


def test_three_teas_present(seeded_engine):
    with make_session(seeded_engine) as s:
        ids = {row[0] for row in s.execute(select(models.Tea.id)).all()}
    assert EXPECTED_TEA_IDS <= ids, f"缺茶品：{EXPECTED_TEA_IDS - ids}"


def test_row_counts_match_seed(seeded_engine):
    """每张表行数 == seed list 长度（动态取，不 hardcode）。"""
    seeds = data_loader.all_seeds()
    cases = [
        (models.Tea, "teas"),
        (models.EvidenceSource, "evidence_sources"),
        (models.TeaKnowledge, "tea_knowledge"),
        (models.FlavorProfile, "flavor_profiles"),
        (models.DemoRoute, "demo_routes"),
        (models.GenerationRule, "rules"),
        (models.CrossCulturalTerm, "cross_cultural_terms"),
        (models.ExpressionStrategy, "expression_strategies"),
        (models.Expression, "expressions"),
        (models.Asset, "assets"),
        (models.TraceLink, "trace_nodes"),
    ]
    with make_session(seeded_engine) as s:
        for model, seed_key in cases:
            db_n = len(s.execute(select(model)).all())
            seed_n = len(seeds[seed_key])
            assert db_n == seed_n, f"{model.__tablename__}: DB={db_n} seed={seed_n}"


def test_tea_terms_expanded(seeded_engine):
    """tea_terms 展开：DB 行数 == 各茶术语列表长度之和。"""
    seeds = data_loader.all_seeds()
    expected = sum(len(v) for v in seeds["tea_terms"].values())
    with make_session(seeded_engine) as s:
        db_n = len(s.execute(select(models.TeaTerm)).all())
    assert db_n == expected


def test_trace_root_nodes_have_null_parent(seeded_engine):
    """追溯链根节点（knowledge_*，level 0）parent 为 null，应有 3 个。"""
    with make_session(seeded_engine) as s:
        roots = s.execute(
            select(models.TraceLink).where(models.TraceLink.parent.is_(None))
        ).all()
    assert len(roots) == 3


def test_nested_json_intact(seeded_engine):
    """JSON 列能完整存取嵌套结构（dimensions / outputs / analogy_rules / radar）。"""
    with make_session(seeded_engine) as s:
        # 赛珍珠风味坐标 dimensions 应是 8 维 list
        szz = s.execute(
            select(models.FlavorProfile).where(
                models.FlavorProfile.profile_id == "flavor_szz_tgy_nx"
            )
        ).scalar_one()
        assert isinstance(szz.dimensions, list)
        assert len(szz.dimensions) == 8
        assert all("intensity" in d for d in szz.dimensions)

        # 跨文化表达 analogy_rules 应是 list 非空；国内表达无此字段（null）
        cross = s.execute(
            select(models.Expression).where(
                models.Expression.id == "expr_en_szz_tgy_nx_coffee"
            )
        ).scalar_one()
        assert isinstance(cross.analogy_rules, list) and cross.analogy_rules
        assert "literal_explanation" in cross.outputs

        domestic = s.execute(
            select(models.Expression).where(
                models.Expression.id == "expr_cn_szz_tgy_nx"
            )
        ).scalar_one()
        assert domestic.analogy_rules is None  # 国内表达无此字段
        assert domestic.source_expression_id is None  # 国内表达是翻译源文

        # 物料 radar 是 list 且 value 是 int
        asset = s.execute(
            select(models.Asset).where(models.Asset.id == "asset_szz_poster_en")
        ).scalar_one()
        radar = asset.visual_data["radar"]
        assert isinstance(radar, list) and radar
        assert all(isinstance(r["value"], int) for r in radar)


def test_generated_outputs_is_empty_placeholder(seeded_engine):
    """generated_outputs 仅建空表占位，最小运行时不灌数据。"""
    with make_session(seeded_engine) as s:
        n = len(s.execute(select(models.GeneratedOutput)).all())
    assert n == 0


def test_idempotent_reseed(tmp_path):
    """连续两次 --reset 行数一致（删旧库重建不残留）。"""
    db_path = tmp_path / "tea.db"
    first = run_seed(reset=True, db_path=db_path, verbose=False)
    second = run_seed(reset=True, db_path=db_path, verbose=False)
    assert first == second

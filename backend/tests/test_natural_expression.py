"""自然语言入口（POST /api/natural-expression）测试。

Fork A：NL → 意图解析 LLM（输出 tea_id + chain）→ 复用现有表达链路。
两条链一并支持：默认 domestic，明确要求英文 / 西方 / 海外时走 cross_cultural。
directive = 原始 NL 文本，透传给话术 LLM 的 prompt。

策略：conftest 默认 LLM disabled，本文件用 autouse fixture 覆盖为 enabled，
但用 monkeypatch 替换 llm_service.generate 为可控桩，不真调 LLM。
intent 解析与话术生成各调一次 llm_service.generate —— 桩按调用顺序 / prompt
内容区分返回哪种 schema。
"""

import pytest
from fastapi.testclient import TestClient

from app.llm_schemas import (
    CrossCulturalExpressionOutputs,
    DomesticExpressionOutputs,
    NaturalLanguageIntent,
)
from app.services import intent_service, llm_service, output_store, prompts
from tests.conftest import _patch_get_settings

# 复用 conftest 的茶品 id
TEA_TGY = "BAMA_SZZ_TGY_NX"  # 铁观音
TEA_DHP = "BAMA_NY_WRT_DHP"  # 大红袍
TEA_JJM = "BAMA_DH_BT_JJM"  # 金骏眉

ENABLED_SETTINGS = __import__("app.config", fromlist=["Settings"]).Settings(
    llm_api_key="fake-key-for-testing",
    llm_base_url="https://fake.example.com",
    llm_model="fake-model",
    llm_supports_json_mode=True,
)


@pytest.fixture(autouse=True)
def _enable_llm(monkeypatch, client: TestClient):
    """覆盖 conftest 的 disabled 默认：本文件让 llm_enabled=True。

    conftest 的 llm_disabled（autouse）先 setup 设 disabled；本 fixture 后
    setup，覆盖成 enabled。teardown 时 conftest 已清，不污染其他文件。
    """
    _patch_get_settings(monkeypatch, ENABLED_SETTINGS)
    yield


# ---------------------------------------------------------------------------
# 桩：把意图解析与话术生成区分开（按 output_model 类型路由返回值）
# ---------------------------------------------------------------------------


def _make_generate(monkeypatch, *, intent_out, domestic_out=None, cross_out=None, calls=None):
    """构造一个按 output_model 类型分发返回值的 generate 桩。

    intent_out：意图解析应返回的 (dict, status)。
    domestic_out / cross_out：话术生成应返回的 (dict, status)。
    calls：可选 list，记录每次调用的 output_model 以便断言调用次数 / 顺序。
    """
    def fake_generate(*, system_prompt, user_prompt, output_model):
        if calls is not None:
            calls.append(output_model)
        if output_model is NaturalLanguageIntent:
            return intent_out
        if output_model is DomesticExpressionOutputs:
            return domestic_out if domestic_out is not None else (None, "parse_error")
        if output_model is CrossCulturalExpressionOutputs:
            return cross_out if cross_out is not None else (None, "parse_error")
        return (None, "parse_error")

    monkeypatch.setattr(llm_service, "generate", fake_generate)
    return fake_generate


# ---------------------------------------------------------------------------
# (1) intent 命中铁观音 + 默认 domestic → 端到端 domestic shape
# ---------------------------------------------------------------------------


def test_nl_default_domestic_route(client, monkeypatch):
    intent = {"tea_id": TEA_TGY, "chain": "domestic"}
    domestic = {
        "story_style": "亲切简短的故事感话术，讲三香。",
        "scientific_style": "成分说明：公开文献代理数据。",
        "emotional_style": "场景化饮用体验。",
    }
    calls = []
    _make_generate(
        monkeypatch,
        intent_out=(intent, "ok"),
        domestic_out=(domestic, "ok"),
        calls=calls,
    )

    resp = client.post(
        "/api/natural-expression",
        json={"text": "给第一次喝铁观音的顾客写一段亲切、简短的三香介绍"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["meta"]["fallback"] is False

    # shape 同 domestic-expression
    d = body["data"]
    assert d["tea_id"] == TEA_TGY
    for k in ("story_style", "scientific_style", "emotional_style"):
        assert d["outputs"][k] == domestic[k]

    # meta.nl
    nl = body["meta"]["nl"]
    assert nl["chain"] == "domestic"
    assert nl["intent_llm_generated"] is True
    assert "三香" in nl["directive"]

    # 走了 LLM 生成话术
    assert body["meta"]["llm_generated"] is True
    assert isinstance(body["meta"]["used_rule_ids"], list)

    # 两次 LLM 调用：先 intent，后话术
    assert calls == [NaturalLanguageIntent, DomesticExpressionOutputs]


# ---------------------------------------------------------------------------
# (2) directive 实际进了国内话术 prompt
# ---------------------------------------------------------------------------


def test_directive_entered_domestic_prompt(client, monkeypatch):
    """directive 文本应出现在 build_domestic_prompt 输出的 user_prompt 里。"""
    intent = {"tea_id": TEA_TGY, "chain": "domestic"}
    domestic = {
        "story_style": "s", "scientific_style": "s", "emotional_style": "s",
    }
    captured = {}

    def fake_generate(*, system_prompt, user_prompt, output_model):
        if output_model is DomesticExpressionOutputs:
            captured["user_prompt"] = user_prompt
        return (domestic, "ok") if output_model is DomesticExpressionOutputs else (
            ({"tea_id": TEA_TGY, "chain": "domestic"}, "ok")
            if output_model is NaturalLanguageIntent else (None, "parse_error")
        )

    monkeypatch.setattr(llm_service, "generate", fake_generate)

    directive = "亲切、简短的三香介绍，面向第一次喝铁观音的顾客"
    client.post("/api/natural-expression", json={"text": directive})

    assert "用户指令" in captured["user_prompt"]
    assert directive in captured["user_prompt"]


# ---------------------------------------------------------------------------
# (3) 越界（"给龙井写个介绍"）→ tea_id=null → fallback
# ---------------------------------------------------------------------------


def test_nl_out_of_scope_tea_returns_fallback(client, monkeypatch):
    """intent LLM 回 null（用户提了清单外的茶）→ 路由层 fallback。"""
    _make_generate(monkeypatch, intent_out=({"tea_id": None, "chain": "domestic"}, "ok"))

    resp = client.post("/api/natural-expression", json={"text": "给龙井写个介绍"})
    body = resp.json()
    assert body["meta"]["fallback"] is True
    assert body["meta"]["fallback_reason"] == "feature_not_available"


def test_nl_hallucinated_tea_id_normalized_to_null(client, monkeypatch):
    """LLM 幻觉编造了一个不在 DB 枚举里的 id → 后端校验归一为 null → fallback。"""
    _make_generate(
        monkeypatch,
        intent_out=({"tea_id": "FAKE_LONGJING_999", "chain": "domestic"}, "ok"),
    )
    resp = client.post("/api/natural-expression", json={"text": "给龙井写个介绍"})
    assert resp.json()["meta"]["fallback"] is True


# ---------------------------------------------------------------------------
# (4) 茶品识别（金骏眉，默认 domestic）
# ---------------------------------------------------------------------------


def test_nl_tea_identification_jjm(client, monkeypatch):
    intent = {"tea_id": TEA_JJM, "chain": "domestic"}
    domestic = {
        "story_style": "s", "scientific_style": "s", "emotional_style": "s",
    }
    _make_generate(
        monkeypatch,
        intent_out=(intent, "ok"),
        domestic_out=(domestic, "ok"),
    )

    resp = client.post("/api/natural-expression", json={"text": "这个金骏眉怎么样"})
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["tea_id"] == TEA_JJM
    assert body["meta"]["nl"]["chain"] == "domestic"


# ---------------------------------------------------------------------------
# (5) 跨文化判定（明确要求英文 / 西方咖啡爱好者）
# ---------------------------------------------------------------------------


def test_nl_cross_cultural_route(client, monkeypatch):
    intent = {"tea_id": TEA_TGY, "chain": "cross_cultural"}
    cross = {
        "literal_explanation": "en literal",
        "beginner_analogy": "en analogy",
        "cultural_narrative": "en narrative",
        "analogy_rules": [
            {
                "source_dimension": "花香",
                "target_reference": "floral finish in washed coffee",
                "confidence": "medium",
                "note": "入门类比",
            }
        ],
    }
    calls = []
    _make_generate(
        monkeypatch,
        intent_out=(intent, "ok"),
        cross_out=(cross, "ok"),
        calls=calls,
    )

    resp = client.post(
        "/api/natural-expression",
        json={"text": "用英文给西方咖啡爱好者介绍铁观音"},
    )
    body = resp.json()
    assert body["success"] is True
    assert body["meta"]["fallback"] is False

    # shape 同 cross-cultural-expression
    d = body["data"]
    assert d["tea_id"] == TEA_TGY
    for k in ("literal_explanation", "beginner_analogy", "cultural_narrative"):
        assert d["outputs"][k] == cross[k]
    assert d["analogy_rules"] == cross["analogy_rules"]
    # source_expression_id 仍指向国内 seed（横向翻译派生关系保留）
    assert d["source_expression_id"] == "expr_cn_szz_tgy_nx"

    nl = body["meta"]["nl"]
    assert nl["chain"] == "cross_cultural"
    assert nl["intent_llm_generated"] is True

    assert calls == [NaturalLanguageIntent, CrossCulturalExpressionOutputs]


# ---------------------------------------------------------------------------
# (6) directive 实际进了跨文化话术 prompt（对称）
# ---------------------------------------------------------------------------


def test_directive_entered_cross_cultural_prompt(client, monkeypatch):
    captured = {}

    def fake_generate(*, system_prompt, user_prompt, output_model):
        if output_model is CrossCulturalExpressionOutputs:
            captured["user_prompt"] = user_prompt
        if output_model is NaturalLanguageIntent:
            return ({"tea_id": TEA_TGY, "chain": "cross_cultural"}, "ok")
        if output_model is CrossCulturalExpressionOutputs:
            return ({
                "literal_explanation": "x", "beginner_analogy": "x",
                "cultural_narrative": "x", "analogy_rules": [],
            }, "ok")
        return (None, "parse_error")

    monkeypatch.setattr(llm_service, "generate", fake_generate)

    directive = "keep it short and friendly for Western coffee lovers"
    client.post("/api/natural-expression", json={"text": directive})

    assert "用户指令" in captured["user_prompt"]
    assert directive in captured["user_prompt"]


# ---------------------------------------------------------------------------
# (7) LLM 未启用 → NL endpoint fallback + 现有三接口仍 seed 兜底（回归）
# ---------------------------------------------------------------------------


def test_nl_llm_disabled_returns_fallback(client, monkeypatch):
    """LLM 未启用 → NL 意图无法 seed 兜底，整个接口走 fallback。"""
    from app.config import Settings
    _patch_get_settings(monkeypatch, Settings(llm_api_key="", llm_base_url=""))
    monkeypatch.setattr(
        llm_service, "generate",
        lambda **kw: (_ for _ in ()).throw(AssertionError("未启用不应调 LLM")),
    )
    resp = client.post("/api/natural-expression", json={"text": "给铁观音写个介绍"})
    body = resp.json()
    assert body["meta"]["fallback"] is True
    assert body["meta"]["fallback_reason"] == "feature_not_available"


def test_existing_three_interfaces_still_seed_fallback_when_disabled(client, monkeypatch):
    """回归：未启用 LLM 时现有三接口仍走 seed 兜底（不被 NL 改动影响）。"""
    from app.config import Settings
    _patch_get_settings(monkeypatch, Settings(llm_api_key="", llm_base_url=""))

    dom = client.post(f"/api/teas/{TEA_TGY}/domestic-expression", json={}).json()
    assert dom["meta"]["llm_generated"] is False
    assert "llm_fallback_reason" not in dom["meta"]

    cc = client.post(
        f"/api/teas/{TEA_TGY}/cross-cultural-expression",
        json={"target_language": "en", "market": "western",
              "audience_reference": "specialty_coffee_lovers"},
    ).json()
    assert cc["meta"]["llm_generated"] is False
    assert "llm_fallback_reason" not in cc["meta"]

    asset = client.post(
        f"/api/teas/{TEA_TGY}/marketing-asset",
        json={"language": "en", "asset_type": "poster"},
    ).json()
    assert asset["meta"]["llm_generated"] is False
    assert "llm_fallback_reason" not in asset["meta"]


# ---------------------------------------------------------------------------
# (8) intent 缓存命中：同 NL 二次调用 → intent 跳过 LLM
# ---------------------------------------------------------------------------


def test_intent_cache_hit_skips_llm(client, monkeypatch):
    """同一 NL 二次调用 → intent 结果命中缓存，不再调 intent LLM。"""
    intent = {"tea_id": TEA_TGY, "chain": "domestic"}
    domestic = {
        "story_style": "s", "scientific_style": "s", "emotional_style": "s",
    }
    intent_calls = []

    def fake_generate(*, system_prompt, user_prompt, output_model):
        if output_model is NaturalLanguageIntent:
            intent_calls.append(1)
            return (intent, "ok")
        if output_model is DomesticExpressionOutputs:
            return (domestic, "ok")
        return (None, "parse_error")

    monkeypatch.setattr(llm_service, "generate", fake_generate)

    text = "给第一次喝铁观音的顾客写一段亲切简短的三香介绍"
    client.post("/api/natural-expression", json={"text": text})
    first_intent_calls = len(intent_calls)
    # 话术每次都会调一次（directive 进 user_prompt，未命中话术缓存时调 LLM）
    # 第二次同 NL：intent 应命中缓存 → intent 调用次数不增
    client.post("/api/natural-expression", json={"text": text})

    assert len(intent_calls) == first_intent_calls, "同 NL 二次调用 intent 应命中缓存"


def test_intent_cached_after_first_call(client, monkeypatch):
    """意图结果写入了 generated_outputs（output_type=natural_language_intent）。"""
    intent = {"tea_id": TEA_DHP, "chain": "domestic"}
    domestic = {
        "story_style": "s", "scientific_style": "s", "emotional_style": "s",
    }
    _make_generate(
        monkeypatch,
        intent_out=(intent, "ok"),
        domestic_out=(domestic, "ok"),
    )

    before = output_store.count_rows()
    client.post("/api/natural-expression", json={"text": "介绍下这款大红袍"})
    after = output_store.count_rows()
    # 至少写入了 intent 缓存 + 话术缓存各 1 行
    assert after > before


# ---------------------------------------------------------------------------
# (9) 回归：现有 domestic-expression / cross-cultural-expression 行为不变
# ---------------------------------------------------------------------------


def test_existing_domestic_endpoint_unchanged(client, monkeypatch):
    """directive=None：现有 domestic-expression 接口的 prompt 不含【用户指令】段。"""
    captured = {}

    def fake_generate(*, system_prompt, user_prompt, output_model):
        if output_model is DomesticExpressionOutputs:
            captured["user_prompt"] = user_prompt
            return ({"story_style": "s", "scientific_style": "s", "emotional_style": "s"}, "ok")
        return (None, "parse_error")

    monkeypatch.setattr(llm_service, "generate", fake_generate)

    client.post(
        f"/api/teas/{TEA_TGY}/domestic-expression",
        json={"audience": {"age_group": "gen_z"}, "style": "store_sales"},
    )
    # 现有接口调用点传 directive=None → prompt 不应出现用户指令围栏
    assert "用户指令" not in captured["user_prompt"]


def test_existing_cross_cultural_endpoint_unchanged(client, monkeypatch):
    captured = {}

    def fake_generate(*, system_prompt, user_prompt, output_model):
        if output_model is CrossCulturalExpressionOutputs:
            captured["user_prompt"] = user_prompt
            return ({
                "literal_explanation": "x", "beginner_analogy": "x",
                "cultural_narrative": "x", "analogy_rules": [],
            }, "ok")
        return (None, "parse_error")

    monkeypatch.setattr(llm_service, "generate", fake_generate)

    client.post(
        f"/api/teas/{TEA_TGY}/cross-cultural-expression",
        json={"target_language": "en", "market": "western",
              "audience_reference": "specialty_coffee_lovers"},
    )
    assert "用户指令" not in captured["user_prompt"]


def test_intent_llm_failure_returns_fallback(client, monkeypatch):
    """意图解析 LLM 失败（如网络错误）→ 路由层 fallback（NL 无 seed 兜底）。"""
    _make_generate(monkeypatch, intent_out=(None, "network_error"))
    resp = client.post("/api/natural-expression", json={"text": "给铁观音写个介绍"})
    body = resp.json()
    assert body["meta"]["fallback"] is True


# ---------------------------------------------------------------------------
# 单元级：build_intent_prompt 把茶品枚举注入约束
# ---------------------------------------------------------------------------


def test_build_intent_prompt_injects_tea_enum():
    tea_list = [
        {"id": TEA_TGY, "name": "赛珍珠浓香型安溪铁观音", "category": "乌龙茶"},
        {"id": TEA_JJM, "name": "金骏眉", "category": "红茶"},
    ]
    system, user = prompts.build_intent_prompt(tea_list, "给铁观音写个介绍")
    # 茶品 id 注入到 user prompt（枚举约束）
    assert TEA_TGY in user
    assert TEA_JJM in user
    # chain 约束 + 默认 domestic 规则注入到 system prompt
    assert "domestic" in system
    assert "cross_cultural" in system
    # 用户输入作为待解析文本注入
    assert "给铁观音写个介绍" in user


def test_normalize_rejects_hallucinated_tea_and_bad_chain():
    """_normalize：tea_id 不在枚举 → None；chain 非法 → domestic。"""
    valid_ids = {TEA_TGY, TEA_JJM, TEA_DHP}
    out = intent_service._normalize(
        {"tea_id": "FAKE_999", "chain": "bogus"}, valid_ids,
    )
    assert out["tea_id"] is None
    assert out["chain"] == "domestic"
    assert out["intent_llm_generated"] is True

    out2 = intent_service._normalize(
        {"tea_id": TEA_TGY, "chain": "cross_cultural"}, valid_ids,
    )
    assert out2["tea_id"] == TEA_TGY
    assert out2["chain"] == "cross_cultural"

"""营销物料接口（层 4）：国内物料 + 跨文化物料。

LLM disabled → copy/image_prompt 走 seed。重点验证：
- 雷达数值来自 seed 事实（visual_data.radar），LLM 不碰
- image_generation_enabled=False（真图仍 P2）
- 国内物料 source_expression_id / 跨文化物料 source_translation_id 纵向指向
"""

from tests.conftest import TEA_ID


def _check_radar(radar):
    assert isinstance(radar, list) and radar
    for r in radar:
        assert "label" in r and "value" in r
        assert isinstance(r["value"], int)  # 事实数据，整数
        assert 0 <= r["value"] <= 10


def test_domestic_asset(client):
    resp = client.post(
        f"/api/teas/{TEA_ID}/marketing-asset",
        json={"language": "zh", "asset_type": "poster"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    d = body["data"]
    assert d["language"] == "zh"
    for k in ("headline", "subheadline", "body"):
        assert isinstance(d["copy"].get(k), str) and d["copy"][k]
    _check_radar(d["visual_data"]["radar"])
    # image_generation_enabled 在 meta 上（responses.success 摊进 meta）
    assert body["meta"]["image_generation_enabled"] is False
    # 国内物料纵向上一级 = 国内表达
    assert d["source_expression_id"] == "expr_cn_szz_tgy_nx"
    assert d.get("source_translation_id") is None
    assert d["trace_id"] == "asset_szz_poster_zh"

    meta = body["meta"]
    assert meta["llm_generated"] is False
    assert "llm_fallback_reason" not in meta


def test_cross_cultural_asset(client):
    resp = client.post(
        f"/api/teas/{TEA_ID}/marketing-asset",
        json={"language": "en", "asset_type": "poster"},
    )
    assert resp.status_code == 200
    d = resp.json()["data"]
    assert d["language"] == "en"
    for k in ("headline", "subheadline", "body"):
        assert isinstance(d["copy"].get(k), str) and d["copy"][k]
    _check_radar(d["visual_data"]["radar"])
    # 跨文化物料纵向上一级 = 跨文化表达
    assert d["source_translation_id"] == "expr_en_szz_tgy_nx_coffee"
    assert d.get("source_expression_id") is None


def test_asset_unsupported_language_fallback(client):
    resp = client.post(
        f"/api/teas/{TEA_ID}/marketing-asset",
        json={"language": "ja", "asset_type": "poster"},
    )
    body = resp.json()
    assert body["meta"]["fallback"] is True


def test_asset_tea_not_found(client):
    resp = client.post("/api/teas/nonexistent/marketing-asset",
                       json={"language": "zh"})
    assert resp.json()["error"]["code"] == "TEA_NOT_FOUND"


def test_asset_platform_and_style_chinese_enum_mapped(client):
    """前端传中文枚举（小红书 / 国风）→ 后端翻成内部英文值后回显。

    LLM disabled → copy 走 seed，platform / style 不影响 seed 文案，
    但应原样回显翻译后的内部值（xiaohongshu / guofeng），不回显中文枚举。
    """
    resp = client.post(
        f"/api/teas/{TEA_ID}/marketing-asset",
        json={"language": "zh", "platform": "小红书", "style": "国风"},
    )
    assert resp.status_code == 200
    d = resp.json()["data"]
    assert d["platform"] == "xiaohongshu", "中文枚举应翻成内部英文值回显"
    assert d["style"] == "guofeng"


def test_asset_platform_internal_value_passthrough(client):
    """前端传内部英文值时原样通过（自映射），不误判。"""
    resp = client.post(
        f"/api/teas/{TEA_ID}/marketing-asset",
        json={"language": "en", "platform": "tiktok"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["platform"] == "tiktok"


def test_asset_platform_unknown_value_passthrough(client):
    """未知平台值不 422，原样透传回显（Demo 友好，前端临时新增枚举不阻断）。"""
    resp = client.post(
        f"/api/teas/{TEA_ID}/marketing-asset",
        json={"language": "zh", "platform": "微博"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["platform"] == "微博"


def test_asset_content_theme_hyphen_to_underscore(client):
    """content_theme 前端连字符值 → 后端下划线内部值回显。"""
    resp = client.post(
        f"/api/teas/{TEA_ID}/marketing-asset",
        json={"language": "zh", "content_theme": "tea-culture"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["content_theme"] == "tea_culture"


def test_asset_content_theme_optional_absent(client):
    """不传 content_theme 时响应不含该键。"""
    resp = client.post(
        f"/api/teas/{TEA_ID}/marketing-asset",
        json={"language": "zh"},
    )
    assert "content_theme" not in resp.json()["data"]

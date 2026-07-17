"""前端中文枚举 → 后端内部英文值映射（app.enum_map）测试。

验证：
- 已知枚举翻成内部值
- None / 空串透传 None（不进 prompt、不进缓存键）
- 未知值不 422、原样透传 + 记 warning
- 抖音 ≠ TikTok（同一 app 但国内/海外两套内部值，不合并）
- 英文内部值自映射（前端已传英文时原样通过，不误判未知）
"""

from app import enum_map


# ---------------------------------------------------------------------------
# platform
# ---------------------------------------------------------------------------


def test_platform_domestic_aliases():
    assert enum_map.resolve_platform("小红书") == "xiaohongshu"
    assert enum_map.resolve_platform("抖音") == "douyin"
    assert enum_map.resolve_platform("微信视频号") == "wechat_channels"


def test_platform_overseas_aliases():
    assert enum_map.resolve_platform("Instagram") == "instagram"
    assert enum_map.resolve_platform("TikTok") == "tiktok"
    assert enum_map.resolve_platform("YouTube") == "youtube"


def test_platform_douyin_neq_tiktok():
    """抖音与 TikTok 映射到不同内部值，不合并。"""
    assert enum_map.resolve_platform("抖音") != enum_map.resolve_platform("TikTok")
    assert enum_map.resolve_platform("抖音") == "douyin"
    assert enum_map.resolve_platform("TikTok") == "tiktok"


def test_platform_none_and_empty():
    assert enum_map.resolve_platform(None) is None
    assert enum_map.resolve_platform("") is None


def test_platform_unknown_value_passthrough(caplog):
    """未知平台值不阻断：原样透传 + 记 warning。"""
    import logging

    with caplog.at_level(logging.WARNING, logger="app.enum_map"):
        result = enum_map.resolve_platform("微博")
    assert result == "微博", "未知值应原样透传，不丢弃"
    assert any("platform" in r.message for r in caplog.records), "应记 warning"


def test_platform_internal_value_self_mapped():
    """前端已传内部英文值时原样通过（自映射），不误判为未知。"""
    assert enum_map.resolve_platform("tiktok") == "tiktok"
    assert enum_map.resolve_platform("xiaohongshu") == "xiaohongshu"


# ---------------------------------------------------------------------------
# marketing-asset style（≠ 生图 style fresh/business）
# ---------------------------------------------------------------------------


def test_marketing_style_aliases():
    assert enum_map.resolve_marketing_style("年轻") == "youthful"
    assert enum_map.resolve_marketing_style("商务") == "business"
    assert enum_map.resolve_marketing_style("国风") == "guofeng"


def test_marketing_style_none_and_empty():
    assert enum_map.resolve_marketing_style(None) is None
    assert enum_map.resolve_marketing_style("") is None


def test_marketing_style_unknown_value_passthrough(caplog):
    import logging

    with caplog.at_level(logging.WARNING, logger="app.enum_map"):
        result = enum_map.resolve_marketing_style("赛博朋克")
    assert result == "赛博朋克"
    assert any("marketing-asset style" in r.message for r in caplog.records)


def test_marketing_style_internal_value_self_mapped():
    """英文内部值自映射：前端传 youthful 原样通过。"""
    assert enum_map.resolve_marketing_style("youthful") == "youthful"
    assert enum_map.resolve_marketing_style("guofeng") == "guofeng"


# ---------------------------------------------------------------------------
# expression tone（国内链 + 跨文化链共用）
# ---------------------------------------------------------------------------


def test_expression_tone_aliases():
    assert enum_map.resolve_expression_tone("温润亲切") == "warm"
    assert enum_map.resolve_expression_tone("专业严谨") == "professional"
    assert enum_map.resolve_expression_tone("诗意古风") == "poetic"
    assert enum_map.resolve_expression_tone("活泼年轻") == "lively"
    assert enum_map.resolve_expression_tone("商务克制") == "restrained_business"


def test_expression_tone_none_and_empty():
    assert enum_map.resolve_expression_tone(None) is None
    assert enum_map.resolve_expression_tone("") is None


def test_expression_tone_unknown_passthrough(caplog):
    import logging

    with caplog.at_level(logging.WARNING, logger="app.enum_map"):
        result = enum_map.resolve_expression_tone("中二病")
    assert result == "中二病"
    assert any("expression tone" in r.message for r in caplog.records)


def test_expression_tone_internal_value_self_mapped():
    assert enum_map.resolve_expression_tone("warm") == "warm"
    assert enum_map.resolve_expression_tone("poetic") == "poetic"


# ---------------------------------------------------------------------------
# expression length
# ---------------------------------------------------------------------------


def test_expression_length_aliases():
    assert enum_map.resolve_expression_length("短（80字内）") == "short"
    assert enum_map.resolve_expression_length("中（80-200字）") == "medium"
    assert enum_map.resolve_expression_length("长（200字以上）") == "long"


def test_expression_length_none_and_empty():
    assert enum_map.resolve_expression_length(None) is None
    assert enum_map.resolve_expression_length("") is None


def test_expression_length_unknown_passthrough(caplog):
    import logging

    with caplog.at_level(logging.WARNING, logger="app.enum_map"):
        result = enum_map.resolve_expression_length("大概三句话")
    assert result == "大概三句话"
    assert any("expression length" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# content_theme（连字符 → 下划线）
# ---------------------------------------------------------------------------


def test_content_theme_hyphen_to_underscore():
    assert enum_map.resolve_content_theme("tea-marketing") == "tea_marketing"
    assert enum_map.resolve_content_theme("tea-culture") == "tea_culture"


def test_content_theme_none_and_empty():
    assert enum_map.resolve_content_theme(None) is None
    assert enum_map.resolve_content_theme("") is None


def test_content_theme_unknown_passthrough(caplog):
    import logging

    with caplog.at_level(logging.WARNING, logger="app.enum_map"):
        result = enum_map.resolve_content_theme("tea-history")
    assert result == "tea-history", "未知值原样透传，连字符也保留"
    assert any("content_theme" in r.message for r in caplog.records)


def test_content_theme_underscore_self_mapped():
    """前端已传下划线内部值时原样通过。"""
    assert enum_map.resolve_content_theme("tea_marketing") == "tea_marketing"
    assert enum_map.resolve_content_theme("tea_culture") == "tea_culture"

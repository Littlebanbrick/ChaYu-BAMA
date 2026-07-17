"""Pydantic schemas：请求体校验 + 文档化。

Demo 调试友好：不强制前端传齐所有字段，请求体字段均设默认值。
字段含义见 docs/接口文档.md；字段变更须同步更新该文档。
"""

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 5.1 国内表达
# ---------------------------------------------------------------------------


class DomesticAudience(BaseModel):
    age_group: str | None = Field(default="gen_z", description="年龄段")
    knowledge_level: str | None = Field(default="beginner", description="茶知识水平")
    scenario: str | None = Field(default="self_drinking", description="饮用场景")
    psychology: str | None = Field(default="curiosity", description="消费心理")


class DomesticExpressionRequest(BaseModel):
    audience: DomesticAudience = Field(default_factory=DomesticAudience)
    style: str | None = Field(default="store_sales", description="表达风格，如 store_sales")
    tone: str | None = Field(
        default=None,
        description=(
            "语气 hint。前端可传中文枚举（温润亲切/专业严谨/诗意古风/活泼年轻/商务克制），"
            "后端按 app.enum_map 翻成内部英文值（warm/professional/poetic/lively/"
            "restrained_business）；未知值原样透传。注入 prompt 影响话术调性，不强制枚举。"
        ),
    )
    length: str | None = Field(
        default=None,
        description=(
            "篇幅 hint。前端可传中文枚举（短（80字内）/中（80-200字）/长（200字以上）），"
            "后端按 app.enum_map 翻成内部英文值（short/medium/long）；未知值透传。注入 prompt。"
        ),
    )
    time_node: str | None = Field(
        default=None,
        description=(
            "时间节点 hint。自由文本（如'中秋''双11''圣诞节'），不经枚举映射、原样透传进 prompt，"
            "让 LLM 结合节点生成场景化话术。国内 / 海外节点都走本字段，不区分。"
        ),
    )


# ---------------------------------------------------------------------------
# 5.2 跨文化表达
# ---------------------------------------------------------------------------


class CrossCulturalExpressionRequest(BaseModel):
    target_language: str = Field(default="en", description="目标语言，Demo 阶段仅 en")
    market: str = Field(default="western", description="目标市场，Demo 阶段仅 western")
    audience_reference: str = Field(
        default="specialty_coffee_lovers", description="受众参照系"
    )
    audience_level: str | None = Field(default="beginner")
    preserve_chinese_terms: bool | None = Field(default=True)
    tone: str | None = Field(
        default=None,
        description=(
            "语气 hint，与国内表达同一套枚举（温润亲切/专业严谨/... → warm/professional/...）。"
            "未知值透传。注入 prompt。"
        ),
    )
    length: str | None = Field(
        default=None,
        description="篇幅 hint（短（80字内）/中（80-200字）/长（200字以上）→ short/medium/long）。未知值透传。注入 prompt。",
    )
    time_node: str | None = Field(
        default=None,
        description="时间节点 hint，自由文本（如'圣诞节''Prime会员日'）原样透传进 prompt。国内 / 海外节点都走本字段。",
    )


# ---------------------------------------------------------------------------
# 5.3 自然语言表达（NL 入口）
# ---------------------------------------------------------------------------


class NaturalExpressionRequest(BaseModel):
    """自然语言表达请求：用户输入一段自由文本，后端解析意图后复用现有表达链路。

    前端只传 text（如"给第一次喝铁观音的顾客写段亲切简短的三香介绍"），
    茶品识别与链路判定由后端意图解析负责，无需前端传 tea_id。
    """

    text: str = Field(..., description="用户自然语言输入，描述想要的茶品表达")


# ---------------------------------------------------------------------------
# 6.1 营销物料
# ---------------------------------------------------------------------------


class MarketingAssetRequest(BaseModel):
    route_id: str | None = Field(default=None, description="Demo 路径 ID")
    asset_type: str = Field(default="poster")
    platform: str | None = Field(
        default=None,
        description=(
            "投放平台。前端可传中文枚举（小红书/抖音/微信视频号/Instagram/TikTok/YouTube），"
            "后端按 app.enum_map 翻成内部英文值（xiaohongshu/douyin/wechat_channels/"
            "instagram/tiktok/youtube）；抖音 ≠ TikTok 不合并。未知值原样透传不报错。"
        ),
    )
    language: str = Field(default="en", description="zh=国内物料 / en=跨文化物料")
    style: str | None = Field(
        default="premium_but_approachable",
        description=(
            "物料风格。前端可传中文枚举（年轻/商务/国风），后端按 app.enum_map 翻成"
            "内部英文值（youthful/business/guofeng）；未知值原样透传。"
            "注意：与生图接口 §6.2 的 style（fresh/business）是两套维度——本字段管文案调性，"
            "生图 style 管画面光照色调。"
        ),
    )
    content_theme: str | None = Field(
        default=None,
        description=(
            "内容主题。前端 value 为 tea-marketing（茶叶营销，突出卖点/促销/礼盒）/"
            "tea-culture（茶文化，传播茶道/产地/工艺）。后端按 app.enum_map 翻成内部下划线值"
            "（tea_marketing / tea_culture）；未知值透传。注入 prompt 决定文案侧重营销还是文化叙事。"
        ),
    )


# ---------------------------------------------------------------------------
# 6.2 生图（image/generate）
# ---------------------------------------------------------------------------


class ImageGenerateRequest(BaseModel):
    prompt: str = Field(..., description="图片生成 prompt（通常来自 marketing-asset.image_prompt）")
    size: str | None = Field(default=None, description="如 2K / 1024x1024；空用配置默认")
    style: str | None = Field(default=None, description="风格：fresh / business；空用默认 fresh")
    scene: str | None = Field(default=None, description="镜头：closeup / landscape / product；空用默认 closeup")
    tea_id: str | None = Field(default=None, description="溯源用，兼配合 language 取 seed copy 印进图")
    route_id: str | None = Field(default=None, description="溯源用，不参与生图")
    language: str | None = Field(default=None, description="zh/en；配合 tea_id 后端取 seed copy 印进图；空则纯画面出图")


# ---------------------------------------------------------------------------
# 8.1 Fallback
# ---------------------------------------------------------------------------


class FallbackRequest(BaseModel):
    feature: str | None = Field(default=None, description="前端标记的功能名")
    requested_path: str | None = Field(default=None, description="前端原本想访问的路径")
    reason: str | None = Field(default="frontend_placeholder")

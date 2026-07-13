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
    platform: str | None = Field(default=None, description="wechat / tiktok 等")
    language: str = Field(default="en", description="zh=国内物料 / en=跨文化物料")
    style: str | None = Field(default="premium_but_approachable")


# ---------------------------------------------------------------------------
# 8.1 Fallback
# ---------------------------------------------------------------------------


class FallbackRequest(BaseModel):
    feature: str | None = Field(default=None, description="前端标记的功能名")
    requested_path: str | None = Field(default=None, description="前端原本想访问的路径")
    reason: str | None = Field(default="frontend_placeholder")

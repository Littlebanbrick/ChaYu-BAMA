"""LLM 输出的 Pydantic 校验模型。

严格校验：所有字段非 Optional、禁止额外字段（extra="forbid"），
confidence 限枚举。任一字段不符 → 校验失败 → 退回 mock 兜底，
避免 LLM 多塞 / 空值悄悄破坏接口契约。

字段形状严格对齐 docs/接口文档.md 中 mock_outputs.yaml 的对应结构。
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class DomesticExpressionOutputs(BaseModel):
    """国内表达三段输出（对齐 strategy_domestic_store_sales.output_slots）。"""

    model_config = ConfigDict(extra="forbid")

    story_style: str
    scientific_style: str
    emotional_style: str


class AnalogyRule(BaseModel):
    """跨文化类比规则子结构。"""

    model_config = ConfigDict(extra="forbid")

    source_dimension: str
    target_reference: str
    confidence: Literal["high", "medium", "low"]
    note: str


class CrossCulturalExpressionOutputs(BaseModel):
    """跨文化表达三段输出 + 类比规则（对齐 strategy_cross_cultural_coffee.output_slots）。"""

    model_config = ConfigDict(extra="forbid")

    literal_explanation: str
    beginner_analogy: str
    cultural_narrative: str
    analogy_rules: list[AnalogyRule]


class AssetCopy(BaseModel):
    """营销物料文案 + image_prompt（雷达数值不在此列，由 seed 事实提供）。"""

    model_config = ConfigDict(extra="forbid")

    headline: str
    subheadline: str
    body: str
    image_prompt: str


class NaturalLanguageIntent(BaseModel):
    """自然语言意图解析输出：识别茶品 tea_id + 判定链路 chain（默认 domestic）。

    tea_id 允许 None：用户提及的茶不在 DB 枚举内、或无法识别时回 null，
    由路由层走 fallback（不假装识别到某款茶）。chain 限枚举：
    domestic（默认）/ cross_cultural（仅当用户明确要求英文 / 西方 / 海外受众）。
    后端会再校验 tea_id ∈ list_teas()、chain ∈ 枚举，防 LLM 幻觉 / 误值。
    """

    model_config = ConfigDict(extra="forbid")

    tea_id: str | None
    chain: Literal["domestic", "cross_cultural"]

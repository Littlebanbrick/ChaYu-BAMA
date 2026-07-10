"""规则库：从结构化规则中按任务/市场/受众/触发术语筛选少量相关规则。

对应 docs/技术架构.md 6.4 节规则筛选流程：
  1. scope 匹配当前任务或 any
  2. market 匹配当前市场或 any
  3. audience_reference 匹配当前受众或 any
  4. trigger_terms 与茶品术语有交集；为空则视为通用规则
  5. 按 priority 排序，取少量高相关规则

阶段一：规则存在内存（mock_data.GENERATION_RULES）。接 SQLite 后改为查表。
注入 prompt 的逻辑在接 LLM 时实现；本阶段返回筛选结果供调试观察。
"""

from app.mock_data import GENERATION_RULES, PRIORITY_ORDER, TEA_TERMS


def select_rules(
    *,
    scope: str,
    market: str,
    audience_reference: str,
    tea_id: str | None = None,
    limit: int = 5,
) -> list[dict]:
    """筛选与当前任务相关的规则。

    Args:
        scope: 任务类型，如 cross_cultural_expression / domestic_expression / marketing_asset
        market: western / domestic
        audience_reference: specialty_coffee_lovers / domestic_general / ...
        tea_id: 用于取茶品术语，与 trigger_terms 取交集；None 时跳过术语命中
        limit: 最多返回规则数
    """
    tea_terms = set(TEA_TERMS.get(tea_id, [])) if tea_id else set()

    matched: list[dict] = []
    for rule in GENERATION_RULES:
        if not rule.get("enabled", True):
            continue
        if rule["scope"] not in (scope, "any"):
            continue
        if rule["market"] not in (market, "any"):
            continue
        if rule["audience_reference"] not in (audience_reference, "any"):
            continue

        triggers = set(rule.get("trigger_terms", []))
        if triggers and not (triggers & tea_terms):
            # 有触发词但当前茶品术语没命中 → 跳过
            continue
        matched.append(rule)

    matched.sort(key=lambda r: PRIORITY_ORDER.get(r.get("priority", "low"), 99))
    return matched[:limit]


def render_rules_for_prompt(rules: list[dict]) -> str:
    """把筛选后的规则渲染成可注入 prompt 的文本（接 LLM 时使用）。"""
    if not rules:
        return "（无匹配规则）"
    lines = []
    for r in rules:
        lines.append(f"- [{r['id']}] {r['instruction']}")
    return "\n".join(lines)

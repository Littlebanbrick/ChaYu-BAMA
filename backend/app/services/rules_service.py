"""规则库：从结构化规则中按任务/市场/受众/触发术语筛选少量相关规则。

对应 docs/技术架构.md 6.4 节规则筛选流程：
  1. scope 匹配当前任务或 any
  2. market 匹配当前市场或 any
  3. audience_reference 匹配当前受众或 any
  4. trigger_terms 与茶品术语有交集；为空则视为通用规则
  5. 按 priority 排序，取少量高相关规则

数据来源：data/seeds/generation_rules.yaml（经 data_loader 加载）。
注入 prompt 的逻辑在接 LLM 时实现；本阶段返回筛选结果供调试观察。
"""

from app import data_loader


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
    tea_terms = set(data_loader.get_tea_terms(tea_id)) if tea_id else set()

    matched: list[dict] = []
    for rule in data_loader.all_rules():
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

    matched.sort(key=lambda r: data_loader.PRIORITY_ORDER.get(r.get("priority", "low"), 99))
    return matched[:limit]


def render_rules_for_prompt(rules: list[dict]) -> str:
    """把筛选后的规则渲染成可注入 prompt 的文本。

    输出规则 id / instruction，并在规则带 negative_example / positive_example
    时一并附上——反面示例是 LLM 真正会尊重的约束（如 rule_marketing_factual_boundary
    的"经八马实测…"正是"不得把代理数据写成八马单品实测值"的关键信号）。
    """
    if not rules:
        return "（无匹配规则）"
    lines: list[str] = []
    for r in rules:
        lines.append(f"- [{r['id']}] {r['instruction']}")
        if r.get("negative_example"):
            lines.append(f"  反例（不得出现）：{r['negative_example']}")
        if r.get("positive_example"):
            lines.append(f"  正例：{r['positive_example']}")
    return "\n".join(lines)

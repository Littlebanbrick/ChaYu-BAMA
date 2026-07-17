# 项目妥协记录（compromises.md）

记录项目中"已实现但当前不启用 / 已决定不做 / 范围红线相关"的决策，供后续恢复或复审时查证。
每条记录 **what / why / 现状 / 恢复条件**，不展开技术细节（技术细节以代码 + 接口文档为准）。

---

## [搁置] NL 自然语言入口 `POST /api/natural-expression`

**日期**：2026-07-18

**What**：NL 入口（意图解析 LLM + directive 透传）已完整实现并通过测试，当前搁置不接入前端。

**Why**：前端输入框经复核为**受控词输入**而非自由文本——用户须按固定格式敲特定词（如"氨基酸""整体总览""特定成分"）触发结构化查询，不接受自由问答。文案的调性 / 长度 / 时间节点已在前置选择中定死，输入框只负责选内容点，两端不重复。NL 入口假设前端发自由文本，与当前前端形态不匹配，接入无收益。

**现状（软搁置）**：
- 代码**全部保留**，不删：`backend/app/services/intent_service.py`、`prompts.build_intent_prompt`、`schemas.NaturalExpressionRequest`、`routers/expressions.py` 的 `/natural-expression` 路由、`expression_service` 的 `directive` 透传链路、`tests/test_natural_expression.py`。
- `docs/接口文档.md §5.3` 标注"已搁置，当前前端不用"，端点仍注册、仍可调，测试仍跑。
- 前端改走结构化接口（`domestic-expression` / `cross-cultural-expression` / `marketing-asset`），语气 / 长度 / 时间节点等通过这些接口的**可选 hint 字段**注入，不依赖 NL。

**恢复条件**：前端若引入真正的自由文本输入框（用户能敲任意一句话），即可重新启用 NL 入口——代码可直接复活，无需重写。**待与前端团队确认**（计划 2026-07 与前端对齐前端输入框的最终形态）。

**相关**：`docs/接口文档.md §5.3`（端点契约）、§1.4 `nl` meta、§10 P1 优先级、`backend/app/services/intent_service.py`。

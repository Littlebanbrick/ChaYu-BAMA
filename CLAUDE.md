# CLAUDE.md

本文件用于 Claude Code 在本仓库中协作开发时快速理解项目目标、工程边界和实现约定。

## 项目状态

本项目处于 Demo 架构和数据准备阶段，项目名称尚未最终确定。当前目标是围绕一条主路径完成可运行后端 Demo：

```text
1 款茶（铁观音） × 欧美市场 × 精品咖啡爱好者 × 图片物料
```

不要默认扩展到多茶品、多语言、多市场或真实视频生成。未开放能力应返回 fallback。

## 必读文档

开发前先阅读：

```text
README.md
docs/技术架构.md
docs/接口文档.md
```

参考资料：

```text
docs/系统架构.pdf
docs/赛题录屏.txt
```

`docs/接口文档.md` 是前后端 API 协作基准。接口字段变更必须同步更新该文档。

## 核心设计

系统采用四层架构：

```text
第 1 层：知识 / 证据层
第 2 层：风味结构化层
第 3 层：表达生成层
第 4 层：营销物料层
```

每层都应能独立输出结果，并尽量能追溯到上一层依据。

核心原则：

```text
结构化知识库约束事实
结构化规则库约束判断
风味坐标承接感知
工作流负责任务拆解
LLM 负责在规则约束下表达转译
物料层负责传播展示
追溯链证明每个输出有依据
fallback 保证未开放功能也能稳定交互
```

## 技术栈约定

后端：

```text
FastAPI
SQLite
SQLAlchemy
Pydantic
YAML / JSON seed 文件
内存缓存
LLM API 可选
```

前端由前端组负责。后端只需保证接口稳定、JSON 字段清晰、Swagger 可调试、fallback 不白屏。

## 数据约定

SQLite 数据库是运行产物，不作为人工维护的数据源。

推荐流程：

```text
backend/data/seeds/*.yaml → backend/scripts/seed.py → backend/data/tea.db
```

`.db` 文件应被 gitignore。

每条关键数据统一字段：

```yaml
id:
type:
claim:
content:
source_type:
source:
confidence:
notes:
```

`source_type` 推荐取值：

```text
public_standard
paper
official_website
ecommerce
interview
social_media
team_assumption
industry_article
```

`confidence` 取值：

```text
high
medium
low
```

Agent 可以辅助收集和格式化科学信息，但来源和可信度由团队人工确认。业务信息以人类调研为主，Agent 只辅助整理。

规则同样是数据，不要硬编码成一个长 prompt。规则应放在 seed 文件中并导入 SQLite，例如：

```text
backend/data/seeds/generation_rules.yaml
```

运行时根据任务、市场、受众和茶品术语筛选相关规则，再注入 LLM prompt。

推荐规则字段：

```yaml
id:
scope:
market:
audience_reference:
trigger_terms:
priority:
instruction:
negative_example:
positive_example:
enabled:
```

## API 优先级

P0 必做：

```http
GET  /api/demo-routes
GET  /api/teas
GET  /api/teas/{tea_id}/knowledge
GET  /api/teas/{tea_id}/flavor-profile
POST /api/teas/{tea_id}/cross-cultural-expression
POST /api/teas/{tea_id}/marketing-asset
GET  /api/trace/{output_id}
```

P1 建议：

```http
POST /api/teas/{tea_id}/domestic-expression
GET  /api/fallback
POST /api/fallback
```

P2 占位：

```http
POST /api/teas/{tea_id}/video-asset
POST /api/translate
POST /api/image/generate
POST /api/audio/generate
GET  /api/markets
GET  /api/audience-references
```

P2 接口可以先注册路由并返回 fallback。

## Fallback 规则

Demo 阶段未开放功能不要返回默认 404 或导致前端白屏。建议对 `/api/*` 未知路由统一返回 fallback JSON：

```json
{
  "success": true,
  "data": {
    "title": "功能暂未开放",
    "message": "该能力已在产品规划中，Demo 阶段暂不提供真实生成结果。",
    "available_route_id": "tieguanyin_western_coffee_poster"
  },
  "meta": {
    "demo_mode": true,
    "fallback": true,
    "fallback_reason": "feature_not_available"
  }
}
```

## 实现建议

优先顺序：

1. 搭建 FastAPI 项目结构。
2. 建 SQLAlchemy models 和 Pydantic schemas。
3. 写 seed 文件和 `seed.py --reset`，包括知识数据、规则数据和 mock 输出。
4. 实现规则筛选函数，例如按 `scope/market/audience_reference/trigger_terms` 取相关规则。
5. 用 mock 数据实现 P0 API。
6. 实现 `/api/*` fallback。
7. 增加追溯链。
8. 后续再接 LLM 和内存缓存。

不要先接真实生图或视频 API。Demo 阶段 `marketing-asset` 返回海报文案、雷达图数据和 `image_prompt` 即可。

## 协作注意

- 不要引入未确定项目名。
- 不要把代理数据写成八马单品实测数据。
- 不要手动维护 SQLite `.db`。
- 不要把缓存结果提交到 Git。
- 不要把所有规则硬编码进 Python 或一个超长 prompt；规则应结构化存储、按需筛选。
- 不要随意修改 API 字段；如需修改，同步更新 `docs/接口文档.md`。
- 保持实现范围围绕主路径，其他能力用 fallback 预留。

# 中国茶 AI 表达 Demo

本项目是一个面向飞书 AI 创赛的 Demo 原型，目标是把中国茶的成分、工艺、风味和文化经验结构化，并进一步转译成国内消费者和海外受众都能理解的表达。

项目名称尚未最终确定，本文档暂以“本项目 / Demo”描述。

## 项目目标

当前 Demo 聚焦主路径：

```text
1 款茶（铁观音）× 图片物料 ×（国内链 + 跨文化链）两条同构链路
```

国内链面向国内消费者，跨文化链面向欧美精品咖啡爱好者。两条链共享同一款茶的知识与风味坐标，跨文化表达由国内表达按规则横向翻译派生而来。

核心思路：

```text
结构化知识库约束事实
结构化规则库约束判断
风味坐标承接感知
工作流负责任务拆解
LLM 负责在规则约束下表达转译
物料层负责传播展示
纵向追溯链证明每个输出有事实依据
翻译与类比为同层横向派生，不进纵向链
fallback 保证未开放功能也能稳定交互
```

## 功能范围

P0 必做接口：

```http
GET  /api/demo-routes
GET  /api/teas
GET  /api/teas/{tea_id}/knowledge
GET  /api/teas/{tea_id}/flavor-profile
POST /api/teas/{tea_id}/domestic-expression
POST /api/teas/{tea_id}/cross-cultural-expression
POST /api/teas/{tea_id}/marketing-asset
GET  /api/trace/{output_id}
```

国内链与跨文化链均为主路径，`domestic-expression` 升级为 P0：它是跨文化表达横向翻译的源文，且国内物料同样走到物料层。

P1 建议接口：

```http
GET  /api/fallback
POST /api/fallback
```

P2 占位接口：

```http
POST /api/teas/{tea_id}/video-asset
POST /api/translate
POST /api/image/generate
POST /api/audio/generate
GET  /api/markets
GET  /api/audience-references
```

详细接口定义见 [docs/接口文档.md](./docs/接口文档.md)。

## 技术栈

后端：

```text
FastAPI
SQLite
SQLAlchemy
Pydantic
YAML / JSON seed 文件
内存缓存
LLM API（豆包 / 通义千问 / OpenAI-compatible API 均可）
```

前端：

```text
由前端组决定
```

Demo 阶段不强依赖真实生图 API。后端优先返回海报文案、雷达图数据和图片 prompt，由前端模板渲染。

## 架构说明

系统采用“四层功能 + 三类底座”的架构。

四层功能：

```text
第 1 层：知识 / 证据层   （成分：茶品事实、工艺、成分、文化）
第 2 层：风味结构化层     （感知：成分 → 风味坐标）
第 3 层：表达生成层       （具象化：感知 → 可理解话术）
第 4 层：营销物料层       （多模态物料：表达 → 海报 / 雷达 / image_prompt）
```

四层在第 3、4 层各自分出国内、跨文化两条同构链路，共享第 1、2 层茶品事实。跨文化表达由国内表达按规则横向翻译派生而来——这是同层横向派生，不进入纵向追溯链。

每一层都应能独立输出结果，并能纵向追溯到上一层依据。国内链与跨文化链各自纵向追溯，结构对称、各四层；翻译关系通过 `source_expression_id` 字段另行记录。

三类底座：

```text
知识库：系统知道什么，例如茶品、产地、工艺、成分、风味术语和调研洞察。
规则库：系统如何判断，例如什么时候可以类比咖啡、什么时候必须保留中国茶概念、哪些表达不能写成事实。
工作流：系统按什么步骤完成任务，例如检索茶品数据、筛选规则、构造 prompt、生成结果、写入追溯链。
```

详细架构见 [docs/技术架构.md](./docs/技术架构.md)。

## 数据策略

SQLite 数据库只作为运行产物，不作为人工维护的数据源。

推荐流程：

```text
seed YAML / JSON → seed.py → SQLite
```

Git 中提交：

```text
backend/data/seeds/*.yaml
backend/scripts/seed.py
```

Git 中忽略：

```text
backend/data/tea.db
```

规则也作为结构化数据维护，不硬编码成长 prompt。推荐流程：

```text
generation_rules.yaml → seed.py → generation_rules 表 → 按任务动态筛选相关规则 → 注入 prompt
```

例如生成跨文化表达时，需要筛选跨文化表达、欧美市场、咖啡爱好者、观音韵/花香/回甘相关规则，以及“国内表达→国外表达”翻译规则，而不是每次传输全部规则。

## 数据收集范围

数据分为三类。

科学信息：

```text
茶品基础信息
产地风土信息
制作工艺信息
成分与感知关系
风味术语 / 风味轮相关信息
铁观音 Demo 风味坐标
```

业务信息：

```text
海外消费者对中国茶的理解差异
精品咖啡爱好者可接受的类比表达
海外社媒上中国茶内容的传播方式
茶叶爱好者对“韵”“回甘”“兰花香”等概念的理解
八马 / 茶叶销售员真实话术
团队调研得到的表达策略
```

规则信息：

```text
跨文化类比边界
中国茶文化概念保留策略
面向不同受众的表达策略
营销文案事实边界
输出格式和示例约束
```

科学信息和业务信息统一字段：

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

规则信息使用独立字段：

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

`confidence` 推荐取值：

```text
high
medium
low
```

科学信息可以由 Agent 自动化收集公开资料并整理成 seed 文件，但关键结论需要团队人工确认来源和可信度。业务信息应以人类调研为主，Agent 负责辅助整理、打标签和转成 seed 格式。

## 推荐目录结构

```text
backend/
  app/
    main.py
    database.py
    models.py
    schemas.py
    routers/
      teas.py
      expressions.py
      assets.py
      trace.py
      fallback.py
    services/
      knowledge_service.py
      flavor_service.py
      expression_service.py
      asset_service.py
      trace_service.py
      llm_service.py
    prompts/
      domestic_expression.py
      cross_cultural_expression.py
      marketing_asset.py
    cache/
      cache_manager.py
  data/
    tea.db
    seeds/
      teas.yaml
      evidence.yaml
      flavor_profiles.yaml
      generation_rules.yaml
      expression_strategies.yaml
      demo_routes.yaml
      cross_cultural_terms.yaml
      mock_outputs.yaml
  scripts/
    seed.py
  requirements.txt

frontend/
  ...

README.md
CLAUDE.md
docs/
  接口文档.md
  技术架构.md
  系统架构.pdf
  赛题录屏.txt
```

## 环境变量

后端后续接入 LLM 或生图服务时，可使用：

```bash
LLM_API_KEY=xxx
LLM_API_BASE_URL=xxx
LLM_MODEL=xxx
IMAGE_API_KEY=xxx
```

Demo 初期可以先使用 mock 输出，不强制配置上述环境变量。

## 本地运行

当前仓库仍处于架构和数据准备阶段。后端代码创建后，推荐运行方式如下：

```bash
cd backend
pip install -r requirements.txt
python scripts/seed.py --reset
uvicorn app.main:app --reload
```

启动后访问：

```text
http://localhost:8000/docs
```

查看 FastAPI 自动生成的接口文档。

## Fallback 约定

Demo 阶段未开放的功能不要直接报错或白屏。后端应统一返回 fallback JSON。

示例：

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

建议对 `/api/*` 的未知路由设置全局 fallback。

## 当前文档

```text
README.md              项目总览
CLAUDE.md              Claude Code 协作说明
docs/接口文档.md        前后端 API 协作基准
docs/技术架构.md        系统架构、数据流和实现原则
docs/系统架构.pdf       产品侧架构参考
docs/赛题录屏.txt       赛题文本整理
```

## Contributors

```text
李雨昕、彭诗瑄、王传宇
```

## License

```text
NO LICENSE
```

当前仓库未声明开源许可证。除团队内部协作和赛事提交用途外，未经团队明确许可，不默认授权复制、分发、修改或商业使用。

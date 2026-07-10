"""阶段一静态 mock 数据。

对应四层纵向追溯链 + 同层横向翻译派生：
  国内链   ：中文物料 → 国内表达 → 风味坐标 → 知识依据
  跨文化链 ：英文物料 → 跨文化表达 → 风味坐标 → 知识依据

两条链共享同一款茶的知识与风味坐标；跨文化表达由国内表达横向翻译派生，
该关系通过 `source_expression_id` 字段记录，不进入纵向追溯链（trace_nodes）。

Demo 阶段：成分说明统一标注为公开文献代理数据 / 典型范围，不声称单品实测值。
"""

# ---------------------------------------------------------------------------
# 第 1 层：茶品事实 + 知识卡片
# ---------------------------------------------------------------------------

TEAS: dict[str, dict] = {
    "tieguanyin_001": {
        "id": "tieguanyin_001",
        "name": "赛珍珠铁观音",
        "category": "乌龙茶",
        "origin": "福建安溪",
        "brand": "八马茶业",
        "demo_available": True,
    },
}

KNOWLEDGE: dict[str, dict] = {
    "tieguanyin_001": {
        "tea": {
            "id": "tieguanyin_001",
            "name": "赛珍珠铁观音",
            "category": "乌龙茶",
            "origin": "福建安溪",
            "brand": "八马茶业",
        },
        "origin": {
            "region": "福建安溪",
            "terroir": "山地丘陵、云雾充足、昼夜温差较明显，适宜乌龙茶香气形成",
        },
        "process": {
            "name": "铁观音传统制作工艺",
            "steps": ["晒青", "凉青", "摇青", "杀青", "揉捻", "焙火"],
            "key_technique": "看青做青、摇青与焙火控制",
        },
        "story": {
            "title": "铁观音非遗制茶技艺",
            "content": "铁观音制作技艺强调经验判断与工艺控制，是中国乌龙茶的重要代表。",
        },
        "evidence": [
            {
                "id": "evidence_tea_flavor_wheel_2022",
                "source_type": "public_standard",
                "title": "T/CTSS 58-2022 茶叶感官风味轮",
                "source": "T/CTSS 58-2022 茶叶感官风味轮",
                "confidence": "high",
                "note": "Demo 阶段用于风味属性和审评术语参考。source_type、source、confidence 由团队人工确认。",
            }
        ],
    },
}

# ---------------------------------------------------------------------------
# 第 2 层：风味坐标（两条链共享，按 tea_id）
# ---------------------------------------------------------------------------

FLAVOR_PROFILES: dict[str, dict] = {
    "tieguanyin_001": {
        "profile_id": "flavor_tieguanyin_001",
        "tea_id": "tieguanyin_001",
        "dimensions": [
            {
                "key": "floral",
                "label_zh": "花香",
                "label_en": "Floral",
                "intensity": 8,
                "description": "以兰花香为代表的清雅花香",
                "evidence_ids": ["evidence_tea_flavor_wheel_2022"],
            },
            {
                "key": "freshness",
                "label_zh": "鲜爽度",
                "label_en": "Freshness",
                "intensity": 7,
                "description": "入口清爽，回味较明亮",
                "evidence_ids": ["evidence_public_oolong_components"],
            },
            {
                "key": "finish",
                "label_zh": "回甘与尾韵",
                "label_en": "Lingering Finish",
                "intensity": 8,
                "description": "饮后口腔留香，尾韵较长",
                "evidence_ids": ["evidence_tea_flavor_wheel_2022"],
            },
            {
                "key": "roasted",
                "label_zh": "焙火感",
                "label_en": "Roasted Note",
                "intensity": 4,
                "description": "焙火带来的火香与醇厚度",
                "evidence_ids": ["evidence_public_oolong_components"],
            },
        ],
        "component_notes": [
            {
                "name": "氨基酸",
                "value_type": "typical_range",
                "description": "Demo 阶段采用公开文献中的乌龙茶典型范围，不代表八马单品实测值",
            }
        ],
    },
}

# 茶品术语：用于规则筛选时与 trigger_terms 取交集（铁观音 × 欧美 × 咖啡爱好者场景）
TEA_TERMS: dict[str, list[str]] = {
    "tieguanyin_001": ["铁观音", "乌龙茶", "兰花香", "回甘", "观音韵", "清鲜", "韵"],
}

# ---------------------------------------------------------------------------
# 第 3 层：表达生成（国内 + 跨文化，同层对等）
#   跨文化表达 source_expression_id 指向国内表达（横向翻译派生，不进纵向链）
# ---------------------------------------------------------------------------

EXPRESSIONS: dict[str, dict] = {
    "expr_cn_tieguanyin_001": {
        "expression_id": "expr_cn_tieguanyin_001",
        "tea_id": "tieguanyin_001",
        "audience": {
            "age_group": "gen_z",
            "knowledge_level": "beginner",
            "scenario": "self_drinking",
            "psychology": "curiosity",
        },
        "outputs": {
            "story_style": "这款铁观音可以先从香气理解：它不是浓烈的香水感，而是入口后慢慢展开的兰花香。",
            "scientific_style": "它的鲜爽、回甘和花香来自品种、做青和焙火共同作用。Demo 阶段的成分说明采用公开文献代理数据。",
            "emotional_style": "适合在下午慢慢喝，第一口是清爽，后面留下的是比较柔和的花香和回甘。",
        },
        "source_profile_id": "flavor_tieguanyin_001",
        "trace_id": "expr_cn_tieguanyin_001",
    },
    "expr_en_tieguanyin_coffee_001": {
        "translation_id": "expr_en_tieguanyin_coffee_001",
        "tea_id": "tieguanyin_001",
        "target_language": "en",
        "market": "western",
        "audience_reference": "specialty_coffee_lovers",
        "outputs": {
            "literal_explanation": "Guanyin Yun refers to the lingering impression Tieguanyin leaves after drinking, including aroma, aftertaste, and mouthfeel.",
            "beginner_analogy": "For specialty coffee drinkers, think of it as a clean floral finish: not heavy, but memorable after the sip.",
            "cultural_narrative": "In Chinese tea culture, Yun is not only flavor. It describes the rhythm and aftertaste that stay with the drinker.",
        },
        "analogy_rules": [
            {
                "source_dimension": "花香",
                "target_reference": "floral finish in washed coffee",
                "confidence": "medium",
                "note": "用于降低理解门槛，不等同于完全相同的风味物质",
            }
        ],
        "source_profile_id": "flavor_tieguanyin_001",
        "source_expression_id": "expr_cn_tieguanyin_001",
        "trace_id": "expr_en_tieguanyin_coffee_001",
    },
}

# ---------------------------------------------------------------------------
# 第 4 层：营销物料（国内 + 跨文化，同等重要、相同生成方式）
#   国内物料 source_expression_id 指向国内表达（纵向上一级）
#   跨文化物料 source_translation_id 指向跨文化表达（纵向上一级）
# ---------------------------------------------------------------------------

ASSETS: dict[str, dict] = {
    "asset_tieguanyin_poster_zh_001": {
        "asset_id": "asset_tieguanyin_poster_zh_001",
        "tea_id": "tieguanyin_001",
        "asset_type": "poster",
        "platform": "wechat",
        "language": "zh",
        "copy": {
            "headline": "一杯讲得清的铁观音",
            "subheadline": "兰花香、清爽鲜爽、回甘悠长",
            "body": "传统安溪铁观音，入口清爽，兰花香缓缓展开，饮后留香悠长。",
        },
        "visual_data": {
            "radar": [
                {"label": "花香", "value": 8},
                {"label": "鲜爽度", "value": 7},
                {"label": "回甘与尾韵", "value": 8},
                {"label": "焙火感", "value": 4},
            ]
        },
        "image_prompt": "面向国内消费者的铁观音海报，兰花、白瓷茶杯、清雅花韵氛围，现代排版。",
        "source_expression_id": "expr_cn_tieguanyin_001",
        "trace_id": "asset_tieguanyin_poster_zh_001",
    },
    "asset_tieguanyin_poster_en_001": {
        "asset_id": "asset_tieguanyin_poster_en_001",
        "tea_id": "tieguanyin_001",
        "asset_type": "poster",
        "platform": "tiktok",
        "language": "en",
        "copy": {
            "headline": "Tieguanyin, Explained Like Specialty Coffee",
            "subheadline": "Floral aroma, clean freshness, and a lingering finish.",
            "body": "A Chinese oolong tea with a graceful floral profile and a finish that stays after the sip.",
        },
        "visual_data": {
            "radar": [
                {"label": "Floral", "value": 8},
                {"label": "Freshness", "value": 7},
                {"label": "Lingering Finish", "value": 8},
                {"label": "Roasted Note", "value": 4},
            ]
        },
        "image_prompt": "Premium poster for Chinese Tieguanyin oolong tea, designed for Western specialty coffee lovers, elegant tea leaves, porcelain cup, clear floral mood, modern editorial layout.",
        "source_translation_id": "expr_en_tieguanyin_coffee_001",
        "trace_id": "asset_tieguanyin_poster_en_001",
    },
}

# ---------------------------------------------------------------------------
# 纵向追溯链节点（每节点带 parent = 纵向上一级 id；横向翻译关系不在此处）
#   level 与架构层号方向相反：3=物料、2=表达、1=风味坐标、0=知识依据
# ---------------------------------------------------------------------------

TRACE_NODES: dict[str, dict] = {
    "asset_tieguanyin_poster_en_001": {
        "node_type": "marketing_asset",
        "level": 3,
        "name": "多模态物料",
        "summary": "面向欧美咖啡爱好者的英文图片物料",
        "parent": "expr_en_tieguanyin_coffee_001",
    },
    "asset_tieguanyin_poster_zh_001": {
        "node_type": "marketing_asset",
        "level": 3,
        "name": "多模态物料",
        "summary": "面向国内消费者的中文图片物料",
        "parent": "expr_cn_tieguanyin_001",
    },
    "expr_en_tieguanyin_coffee_001": {
        "node_type": "expression",
        "level": 2,
        "name": "跨文化表达",
        "summary": "用 specialty coffee 的 floral finish 降低理解门槛，同时保留 Guanyin Yun 的文化解释",
        "parent": "flavor_tieguanyin_001",
    },
    "expr_cn_tieguanyin_001": {
        "node_type": "expression",
        "level": 2,
        "name": "国内表达",
        "summary": "兰花香、清爽、尾韵较长",
        "parent": "flavor_tieguanyin_001",
    },
    "flavor_tieguanyin_001": {
        "node_type": "flavor_profile",
        "level": 1,
        "name": "风味坐标",
        "summary": "花香 8，鲜爽度 7，回甘与尾韵 8",
        "parent": "knowledge_tieguanyin_001",
    },
    "knowledge_tieguanyin_001": {
        "node_type": "knowledge",
        "level": 0,
        "name": "知识依据",
        "summary": "铁观音工艺、乌龙茶审评术语、公开文献代理数据",
        "parent": None,
    },
}

# ---------------------------------------------------------------------------
# Demo 路径：国内链 + 跨文化链两条主路径
# ---------------------------------------------------------------------------

DEMO_ROUTES: list[dict] = [
    {
        "id": "tieguanyin_domestic_poster",
        "tea_id": "tieguanyin_001",
        "tea_name": "赛珍珠铁观音",
        "market": "domestic",
        "target_language": "zh",
        "audience_reference": "domestic_general",
        "asset_type": "poster",
        "enabled": True,
        "description": "铁观音面向国内消费者的中文图片物料 Demo 路径",
    },
    {
        "id": "tieguanyin_western_coffee_poster",
        "tea_id": "tieguanyin_001",
        "tea_name": "赛珍珠铁观音",
        "market": "western",
        "target_language": "en",
        "audience_reference": "specialty_coffee_lovers",
        "asset_type": "poster",
        "enabled": True,
        "description": "铁观音面向欧美精品咖啡爱好者的英文图片物料 Demo 路径",
    },
]

# ---------------------------------------------------------------------------
# 第 3 类底座：结构化规则库（结构来自 generation_rules.yaml 的等价内存版）
#   运行时由 rules_service 按 scope/market/audience_reference/trigger_terms 筛选
# ---------------------------------------------------------------------------

GENERATION_RULES: list[dict] = [
    {
        "id": "rule_domestic_to_foreign_translation",
        "scope": "cross_cultural_expression",
        "market": "western",
        "audience_reference": "any",
        "trigger_terms": [],
        "priority": "high",
        "instruction": "跨文化表达由国内表达横向翻译派生而来。应将国内表达的中文 articulation 信达雅地转译为目标语言，保留原意与文化概念，不得脱离源文自由发挥。该翻译为同层横向派生，不作为纵向追溯链的一层。",
        "negative_example": "忽略国内表达源文，凭空生成一段与源文无关的英文描述。",
        "positive_example": "以国内表达中'兰花香、清爽、尾韵较长'为源文，转译为对应的英文表达。",
        "enabled": True,
    },
    {
        "id": "rule_cross_cultural_preserve_yun",
        "scope": "cross_cultural_expression",
        "market": "western",
        "audience_reference": "specialty_coffee_lovers",
        "trigger_terms": ["观音韵", "韵"],
        "priority": "high",
        "instruction": "涉及观音韵时，不得直接替换成咖啡或葡萄酒术语。必须保留 Guanyin Yun，并提供入门类比和文化解释。",
        "negative_example": "Guanyin Yun is the tannin of tea.",
        "positive_example": "Guanyin Yun can be introduced through a familiar lingering finish, but it is broader than a single coffee or wine note.",
        "enabled": True,
    },
    {
        "id": "rule_domestic_store_sales_style",
        "scope": "domestic_expression",
        "market": "domestic",
        "audience_reference": "domestic_general",
        "trigger_terms": ["兰花香", "回甘"],
        "priority": "medium",
        "instruction": "面向国内消费者的门店话术应通俗易懂，优先用'兰花香、清爽、回甘'等日常感知词，避免生僻审评术语。",
        "negative_example": "本茶具有典型观音韵与醇厚底味。（术语过重）",
        "positive_example": "这款铁观音入口清爽，兰花香慢慢展开，喝完嘴里留香。",
        "enabled": True,
    },
    {
        "id": "rule_marketing_factual_boundary",
        "scope": "marketing_asset",
        "market": "any",
        "audience_reference": "any",
        "trigger_terms": [],
        "priority": "high",
        "instruction": "营销文案不得声称代理数据是八马单品实测值；成分说明须标注为公开文献代理数据或典型范围。",
        "negative_example": "经八马实测，氨基酸含量 X%。",
        "positive_example": "成分说明基于公开文献乌龙茶典型范围，不代表单品实测值。",
        "enabled": True,
    },
]

# 优先级排序权重：规则筛选后按 high > medium > low 排序
PRIORITY_ORDER: dict[str, int] = {"high": 0, "medium": 1, "low": 2}

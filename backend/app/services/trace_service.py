"""纵向追溯链：根据 output_id 组装四层纵向链路。

四层（level 与架构层号方向相反）：
  level 3 = 多模态物料
  level 2 = 表达（国内 / 跨文化）
  level 1 = 风味坐标
  level 0 = 知识依据

横向翻译关系（跨文化表达 ← 国内表达）不进入纵向链；
跨文化表达对象上的 source_expression_id 字段另行记录，前端可按需展示。
"""

from app.mock_data import TRACE_NODES


def build_trace(output_id: str) -> dict | None:
    """组装 output_id 的纵向追溯链。

    Returns:
        {"output_id", "output_type", "trace": [...]} 或 None（id 不存在）。
    """
    node = TRACE_NODES.get(output_id)
    if node is None:
        return None

    trace: list[dict] = []
    current_id = output_id
    while current_id:
        current = TRACE_NODES.get(current_id)
        if current is None:
            break
        trace.append(
            {
                "level": current["level"],
                "name": current["name"],
                "id": current_id,
                "summary": current["summary"],
            }
        )
        current_id = current.get("parent")

    return {
        "output_id": output_id,
        "output_type": TRACE_NODES[output_id]["node_type"],
        "trace": trace,
    }

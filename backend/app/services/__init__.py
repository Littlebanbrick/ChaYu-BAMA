"""服务层（业务逻辑）：被 routers 调用，不碰 HTTP / JSON 响应格式。

阶段一全部基于 mock_data 的内存数据；后续接 SQLite/LLM 时只改这里。
"""

"""配置：从环境变量 / .env 读取 LLM 参数。

明文 key 只放在本地 .env（gitignored），代码里只出现变量引用 + 空默认。
未配置 key 或 base_url 时 llm_enabled=False，生成接口自动走 mock 兜底，
行为与未接 LLM 时一致。

env_file 用绝对路径解析（backend/.env），与 CWD 无关——uvicorn 在 backend/
下运行、容器内运行都能读到。
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """LLM 接入配置。

    所有字段大小写不敏感读取（LLM_API_KEY ↔ llm_api_key）。
    """

    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = "glm-5.2"
    llm_timeout: float = 30.0
    llm_supports_json_mode: bool = True

    @property
    def llm_enabled(self) -> bool:
        """key 与 base_url 都配置了才视为启用。"""
        return bool(self.llm_api_key and self.llm_base_url)

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=None)
def get_settings() -> Settings:
    """单例：整进程读一次 .env。"""
    return Settings()

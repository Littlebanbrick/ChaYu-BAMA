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
    IMAGE_* 是豆包 Seedream（火山方舟 Ark）生图专用，与 LLM_* 相互独立——
    生图不回退 LLM_*（当前 LLM_* 指向 DeepSeek，不覆盖 Ark /images/generations），
    必须独立配 IMAGE_API_KEY / IMAGE_BASE_URL 指向 Ark。
    """

    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = "glm-5.2"
    llm_timeout: float = 30.0
    llm_supports_json_mode: bool = True

    # 豆包 Seedream 生图（火山方舟 Ark；与 LLM_* 相互独立；空 → 生图禁用，不回退 LLM_*）
    image_api_key: str = ""
    image_base_url: str = ""
    image_model: str = "doubao-seedream-5-0-pro-260628"
    image_size: str = "2K"  # Ark 用档位字符串（2K / 1K），不是 1024x1024
    image_quality: str = ""  # Seedream 无 quality 参数；留空不传（CogView 时代遗留字段，Ark 忽略）
    image_timeout: float = 300.0  # Seedream pro 2K 出图偏慢（首图常 >90s）；超时也计费故给足 300s

    @property
    def llm_enabled(self) -> bool:
        """key 与 base_url 都配置了才视为启用。"""
        return bool(self.llm_api_key and self.llm_base_url)

    @property
    def image_enabled(self) -> bool:
        """Ark key 与 base_url 都配置才启用（不回退 LLM_*）。"""
        return bool(self.image_api_key and self.image_base_url)

    def image_credentials(self) -> tuple[str, str]:
        """生图凭证：不回退 LLM_*（当前是 DeepSeek，非 Ark 端点）。"""
        return self.image_api_key, self.image_base_url

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=None)
def get_settings() -> Settings:
    """单例：整进程读一次 .env。"""
    return Settings()

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: Literal["openai_compatible"] = "openai_compatible"
    base_url: str = "http://localhost:1234/v1"
    model: str = Field(default="local-model", min_length=1)
    temperature: float = Field(default=0, ge=0, le=2)
    max_tokens: int = Field(default=2048, gt=0)
    timeout: float = Field(default=120, gt=0)
    max_retries: int = Field(default=2, ge=0)
    structured_output: Literal["auto", "on", "off"] = "auto"

    @field_validator("base_url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        from urllib.parse import urlsplit
        url = urlsplit(value)
        if url.scheme not in {"http", "https"} or not url.hostname:
            raise ValueError("base_url must be an HTTP(S) URL")
        if url.username or url.password or url.query or url.fragment:
            raise ValueError("base_url must not contain credentials, query, or fragment")
        return value.rstrip("/")


class TranslationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_language: str = "en"
    target_language: str = "ru"
    chunk_size: int = Field(default=1500, gt=0)
    context_window: int = Field(default=8192, gt=0)
    glossary_path: Path | None = None


class LoggingConfig(BaseModel):
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", env_nested_delimiter="__", extra="forbid")
    llm: LLMConfig = Field(default_factory=LLMConfig)
    translation: TranslationConfig = Field(default_factory=TranslationConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    llm_api_key: SecretStr = SecretStr("local")

    @classmethod
    def settings_customise_sources(cls, settings_cls, init_settings, env_settings,
                                   dotenv_settings, file_secret_settings):
        return env_settings, init_settings


def load_config(path: Path | None = None, model: str | None = None) -> Settings:
    data = {} if path is None else yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("Configuration must be a YAML mapping")
    if "llm_api_key" in data:
        raise ValueError("Set API credentials through LLM_API_KEY only")
    settings = Settings(**data)
    if model is not None:
        settings.llm = LLMConfig(**{**settings.llm.model_dump(), "model": model})
    glossary = settings.translation.glossary_path
    if path and glossary and not glossary.is_absolute():
        settings.translation.glossary_path = path.resolve().parent / glossary
    return settings

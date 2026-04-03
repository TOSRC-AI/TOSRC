#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pydantic Settings 配置管理

统一管理所有配置，支持环境变量、.env 文件、默认值
"""
import os
from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Dict, Any

from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseSettings):
    """数据库配置"""
    model_config = SettingsConfigDict(env_prefix="DB_")

    url: str = Field(
        default="sqlite:///data/database/tosrc.db",
        description="数据库连接URL"
    )
    use_pool: bool = Field(default=True, description="是否使用连接池")
    pool_max_connections: int = Field(default=10, ge=1, le=100)
    pool_min_connections: int = Field(default=2, ge=1, le=10)
    connection_timeout: float = Field(default=30.0, gt=0)
    max_idle_time: float = Field(default=300.0, gt=0)


class JSONLConfig(BaseSettings):
    """JSONL 日志配置"""
    model_config = SettingsConfigDict(env_prefix="JSONL_")

    enabled: bool = Field(default=True, description="是否启用 JSONL")
    route_log_dir: str = Field(default="data/logs/routes")
    feedback_log_dir: str = Field(default="data/logs/feedback")
    training_data_dir: str = Field(default="data/training")
    buffer_size: int = Field(default=50, ge=0)


class ArchiveConfig(BaseSettings):
    """归档配置"""
    model_config = SettingsConfigDict(env_prefix="ARCHIVE_")

    enabled: bool = Field(default=True, description="是否启用自动归档")
    after_days: int = Field(default=7, ge=1)
    delete_after_days: int = Field(default=90, ge=1)
    compress: bool = Field(default=True)


class SecurityConfig(BaseSettings):
    """安全配置"""
    model_config = SettingsConfigDict(env_prefix="SECURITY_")

    admin_api_key: str = Field(
        default="",
        description="管理后台 API Key"
    )
    api_key_header: str = Field(default="X-Admin-API-Key")
    cors_origins: List[str] = Field(default=["http://localhost:3000"])
    cors_allow_credentials: bool = Field(default=True)
    cors_allow_methods: List[str] = Field(default=["GET", "POST", "PUT", "DELETE"])
    cors_allow_headers: List[str] = Field(default=["Authorization", "Content-Type", "X-Request-ID"])

    @validator("admin_api_key")
    def validate_api_key(cls, v):
        if not v:
            import secrets
            return f"dev-{secrets.token_urlsafe(16)}"
        return v

    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v


class ServiceConfig(BaseSettings):
    """服务配置"""
    model_config = SettingsConfigDict(env_prefix="SERVICE_")

    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8080, ge=1, le=65535)
    workers: int = Field(default=1, ge=1)
    log_level: str = Field(default="INFO")
    reload: bool = Field(default=False, description="开发模式热重载")

    @validator("log_level")
    def validate_log_level(cls, v):
        v = v.upper()
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v not in allowed:
            raise ValueError(f"日志级别必须是 {allowed} 之一")
        return v


class FeatureConfig(BaseSettings):
    """功能开关配置"""
    model_config = SettingsConfigDict(env_prefix="FEATURE_")

    enable_model_engine: bool = Field(default=True)
    enable_bionic_arch: bool = Field(default=True)
    enable_bionic_cache: bool = Field(default=False)
    enable_metrics: bool = Field(default=True)
    enable_sqlite_log: bool = Field(default=True, description="向后兼容")


class Settings(BaseSettings):
    """
    全局配置类

    使用方式：
        from src.config.settings import get_settings

        settings = get_settings()
        print(settings.service.host)
        print(settings.database.url)
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # 忽略未定义的配置项
    )

    # 子配置
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    jsonl: JSONLConfig = Field(default_factory=JSONLConfig)
    archive: ArchiveConfig = Field(default_factory=ArchiveConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    service: ServiceConfig = Field(default_factory=ServiceConfig)
    features: FeatureConfig = Field(default_factory=FeatureConfig)

    # 项目信息
    project_name: str = Field(default="TOSRC")
    version: str = Field(default="1.0.0")
    debug: bool = Field(default=False)

    # 路径配置
    project_root: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent)
    data_dir: Path = Field(default=Path("data"))
    log_dir: Path = Field(default=Path("logs"))

    # 静态资源缓存配置
    cache: Dict[str, Any] = Field(default_factory=lambda: {
        "static_max_age": 86400,  # 1天
        "html_max_age": 300       # 5分钟
    })

    @validator("data_dir", "log_dir")
    def ensure_directory(cls, v):
        """确保目录存在"""
        Path(v).mkdir(parents=True, exist_ok=True)
        return v

    def get_db_path(self) -> str:
        """获取数据库路径（移除 sqlite:/// 前缀）"""
        url = self.database.url
        if url.startswith("sqlite:///"):
            return url.replace("sqlite:///", "")
        return url

    def to_dict(self) -> dict:
        """导出为字典"""
        return self.model_dump()

    def print_config(self, hide_secrets: bool = True):
        """打印配置信息"""
        print(f"\n{'='*50}")
        print(f"{self.project_name} v{self.version} 配置")
        print(f"{'='*50}")

        config_dict = self.to_dict()

        # 递归打印
        def print_dict(d, indent=0):
            for key, value in d.items():
                if isinstance(value, dict):
                    print("  " * indent + f"{key}:")
                    print_dict(value, indent + 1)
                else:
                    # 隐藏敏感信息
                    if hide_secrets and any(secret in key.lower() for secret in ["key", "password", "secret"]):
                        value = "***" if value else ""
                    print("  " * indent + f"{key}: {value}")

        print_dict(config_dict)
        print(f"{'='*50}\n")


@lru_cache()
def get_settings() -> Settings:
    """
    获取配置实例（单例）

    使用 lru_cache 确保整个应用使用同一个配置实例
    """
    return Settings()


# 便捷函数
def get_db_config() -> DatabaseConfig:
    """获取数据库配置"""
    return get_settings().database


def get_security_config() -> SecurityConfig:
    """获取安全配置"""
    return get_settings().security


def get_service_config() -> ServiceConfig:
    """获取服务配置"""
    return get_settings().service


def reload_settings():
    """重新加载配置"""
    get_settings.cache_clear()
    return get_settings()


# 测试代码
if __name__ == "__main__":
    # 加载并打印配置
    settings = get_settings()
    settings.print_config()

    # 测试配置访问
    print(f"数据库URL: {settings.database.url}")
    print(f"服务端口: {settings.service.port}")
    print(f"CORS来源: {settings.security.cors_origins}")

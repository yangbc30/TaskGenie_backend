"""
配置文件
集中管理所有配置项
"""
import os
from typing import Optional

class Settings:
    """应用设置"""
    
    # 应用基本信息
    APP_NAME: str = "TaskGenie"
    APP_VERSION: str = "2.0.0"
    APP_DESCRIPTION: str = "智能任务管理系统"
    
    # API配置
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    
    # AI配置
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "sk-zmyrpclntmuvmufqjclmjczurrexkvzsfcrxthcwzgyffktd")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.siliconflow.cn/v1")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "Qwen/Qwen2.5-7B-Instruct")
    
    # 任务配置
    MAX_TASKS_PER_PLANNING: int = int(os.getenv("MAX_TASKS_PER_PLANNING", "10"))
    DEFAULT_TASK_PRIORITY: str = os.getenv("DEFAULT_TASK_PRIORITY", "medium")
    DEFAULT_ESTIMATED_HOURS: float = float(os.getenv("DEFAULT_ESTIMATED_HOURS", "2.0"))
    
    # 数据库配置（预留，目前使用内存数据库）
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")
    
    # 日志配置
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # CORS配置
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:8081",
        "http://10.0.2.2:8081",  # Android模拟器
        "*"  # 开发环境允许所有来源
    ]
    
    # 缓存配置
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "3600"))  # 1小时
    
    # 任务标签配置
    AUTO_TAG_ENABLED: bool = os.getenv("AUTO_TAG_ENABLED", "True").lower() == "true"
    
    # AI功能配置
    AI_TASK_PLANNING_ENABLED: bool = os.getenv("AI_TASK_PLANNING_ENABLED", "True").lower() == "true"
    AI_SCHEDULE_ENABLED: bool = os.getenv("AI_SCHEDULE_ENABLED", "True").lower() == "true"
    AI_RESPONSE_TIMEOUT: int = int(os.getenv("AI_RESPONSE_TIMEOUT", "30"))  # 30秒
    
    # 安全配置
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# 创建设置实例
settings = Settings()

# 开发环境配置
class DevelopmentSettings(Settings):
    """开发环境设置"""
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"

# 生产环境配置
class ProductionSettings(Settings):
    """生产环境设置"""
    DEBUG: bool = False
    LOG_LEVEL: str = "WARNING"
    CORS_ORIGINS: list = [
        "https://your-frontend-domain.com"
    ]

# 根据环境变量选择配置
def get_settings() -> Settings:
    """根据环境变量获取相应的设置"""
    env = os.getenv("ENVIRONMENT", "development").lower()
    
    if env == "production":
        return ProductionSettings()
    else:
        return DevelopmentSettings()

# 导出当前环境的设置
current_settings = get_settings()
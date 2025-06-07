"""
运行脚本
启动TaskGenie后端服务
"""
import uvicorn
import logging
from config import current_settings

# 配置日志
logging.basicConfig(
    level=getattr(logging, current_settings.LOG_LEVEL),
    format=current_settings.LOG_FORMAT
)

logger = logging.getLogger(__name__)

def main():
    """主函数"""
    logger.info(f"启动 {current_settings.APP_NAME} v{current_settings.APP_VERSION}")
    logger.info(f"环境: {'开发' if current_settings.DEBUG else '生产'}")
    logger.info(f"监听地址: {current_settings.API_HOST}:{current_settings.API_PORT}")
    
    # 启动服务
    uvicorn.run(
        "main:app",
        host=current_settings.API_HOST,
        port=current_settings.API_PORT,
        reload=current_settings.DEBUG,
        log_level=current_settings.LOG_LEVEL.lower()
    )

if __name__ == "__main__":
    main()
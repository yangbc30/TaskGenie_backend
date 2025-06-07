"""
TaskGenie 后端主应用文件
模块化结构的FastAPI应用
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api_routes import task_router, ai_router, general_router

# 创建FastAPI应用
app = FastAPI(
    title="TaskGenie API",
    description="智能任务管理系统API",
    version="2.0.0"
)

# 配置跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(task_router)
app.include_router(ai_router)
app.include_router(general_router)

# 根路径
@app.get("/")
async def root():
    """API根路径"""
    return {
        "message": "TaskGenie API v2.0",
        "description": "智能任务管理系统",
        "features": [
            "多标签任务管理",
            "AI任务规划",
            "智能日程安排",
            "任务统计分析"
        ],
        "docs": "/docs",
        "redoc": "/redoc"
    }

# 健康检查
@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "timestamp": "2024-12-25T10:00:00Z"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
"""
API路由模块
定义所有的API端点
"""
import uuid
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List
from datetime import datetime

from models import (
    Task, TaskCreate, TaskUpdate, AITaskRequest, AIDayScheduleRequest,
    TaskStatsResponse, TagsResponse, AIJob, AIJobStatus
)
from task_service import TaskService
from ai_service import AIService
from tag_service import TagService
from database import db

# 创建路由器
task_router = APIRouter(prefix="/tasks", tags=["tasks"])
ai_router = APIRouter(prefix="/ai", tags=["ai"])
general_router = APIRouter(tags=["general"])

# ===== 任务相关路由 =====
@task_router.post("", response_model=Task)
async def create_task(task: TaskCreate):
    """创建新任务"""
    return TaskService.create_task(task)

@task_router.get("", response_model=List[Task])
async def get_all_tasks():
    """获取所有任务"""
    return TaskService.get_all_tasks()

@task_router.get("/{task_id}", response_model=Task)
async def get_task(task_id: str):
    """获取单个任务"""
    task = TaskService.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task

@task_router.put("/{task_id}", response_model=Task)
async def update_task(task_id: str, task_update: TaskUpdate):
    """更新任务"""
    task = TaskService.update_task(task_id, task_update)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task

@task_router.delete("/{task_id}")
async def delete_task(task_id: str):
    """删除任务"""
    success = TaskService.delete_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"message": "任务已删除"}

@task_router.get("/by-tags")
async def get_tasks_by_tags(tags: str = ""):
    """根据多个标签筛选任务，支持AND逻辑"""
    if not tags:
        return TaskService.get_all_tasks()
    
    # 解析标签字符串（逗号分隔）
    tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
    
    if not tag_list:
        return TaskService.get_all_tasks()
    
    return TaskService.get_tasks_by_tags(tag_list)

@task_router.get("/by-tag/{tag}")
async def get_tasks_by_tag(tag: str):
    """根据单个标签获取任务（兼容旧接口）"""
    return TaskService.get_tasks_by_tag(tag)

@task_router.get("/calendar/{year}/{month}")
async def get_calendar_tasks(year: int, month: int):
    """获取指定月份的任务日历数据"""
    return TaskService.get_calendar_tasks(year, month)

# ===== AI相关路由 =====
@ai_router.post("/plan-tasks/async")
async def ai_plan_tasks_async(request: AITaskRequest, background_tasks: BackgroundTasks):
    """异步 AI 任务规划"""
    job_id = str(uuid.uuid4())
    job = AIJob(
        job_id=job_id,
        status=AIJobStatus.PENDING,
        created_at=datetime.now()
    )
    db.create_ai_job(job)
    
    # 验证和规范化任务数量
    max_tasks = max(1, min(10, request.max_tasks))
    
    print(f"🚀 开始AI任务规划")
    print(f"   目标: {request.prompt}")
    print(f"   任务数量: {max_tasks}")
    print(f"   作业ID: {job_id}")
    
    # 添加后台任务
    background_tasks.add_task(AIService.process_task_planning, job_id, request.prompt, max_tasks)
    
    return {
        "job_id": job_id, 
        "status": "processing",
        "max_tasks": max_tasks,
        "message": f"AI正在为您分析目标并生成{max_tasks}个具体可执行的任务，预计需要10-30秒"
    }

@ai_router.get("/jobs/{job_id}")
async def get_ai_job_status(job_id: str):
    """获取 AI 任务状态"""
    job = db.get_ai_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    return job

@ai_router.post("/schedule-day/async")
async def ai_schedule_day_async(request: AIDayScheduleRequest, background_tasks: BackgroundTasks, force_regenerate: bool = False):
    """异步AI日程安排"""
    job_id = str(uuid.uuid4())
    job = AIJob(
        job_id=job_id,
        status=AIJobStatus.PENDING,
        created_at=datetime.now()
    )
    db.create_ai_job(job)
    
    # 添加后台任务
    background_tasks.add_task(AIService.process_day_schedule, job_id, request.date, request.task_ids, force_regenerate)
    
    return {"job_id": job_id, "status": "processing"}

@ai_router.get("/schedule/{date}")
async def get_day_schedule(date: str):
    """获取指定日期的AI安排"""
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，请使用YYYY-MM-DD格式")
    
    # 检查是否有保存的安排
    schedule = db.get_day_schedule(date)
    if schedule:
        # 检查任务是否发生变化
        current_tasks = db.get_tasks_for_date(target_date)
        current_version = AIService._generate_task_version(current_tasks)
        tasks_changed = schedule.task_version != current_version
        
        return {
            "date": date,
            "has_schedule": True,
            "schedule": schedule,
            "tasks_changed": tasks_changed
        }
    else:
        return {
            "date": date,
            "has_schedule": False,
            "schedule": None,
            "tasks_changed": False
        }

@ai_router.delete("/schedule/{date}")
async def delete_day_schedule(date: str):
    """删除指定日期的AI安排"""
    success = db.delete_day_schedule(date)
    if success:
        return {"message": "安排已删除"}
    else:
        raise HTTPException(status_code=404, detail="该日期没有安排")

@ai_router.get("/schedule-day/{date}")
async def get_day_schedule_preview(date: str):
    """获取指定日期的任务预览"""
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，请使用YYYY-MM-DD格式")
    
    # 收集该日期的任务
    day_tasks = db.get_tasks_for_date(target_date)
    total_estimated_hours = sum(task.estimated_hours or 2.0 for task in day_tasks)
    
    # 统计信息
    high_priority_count = sum(1 for t in day_tasks if t.priority == "high")
    overdue_count = sum(1 for t in day_tasks if t.due_date and t.due_date < datetime.now())
    
    return {
        "date": date,
        "task_count": len(day_tasks),
        "total_estimated_hours": total_estimated_hours,
        "high_priority_count": high_priority_count,
        "overdue_count": overdue_count,
        "tasks": [
            {
                "id": task.id,
                "name": task.name,
                "priority": task.priority,
                "estimated_hours": task.estimated_hours or 2.0,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "task_tags": task.task_tags
            }
            for task in day_tasks
        ]
    }

@ai_router.post("/plan-tasks/test")
async def test_ai_planning(prompt: str = "学习React Native开发", max_tasks: int = 3):
    """测试AI任务规划功能"""
    job_id = str(uuid.uuid4())
    
    try:
        await AIService.process_task_planning(job_id, prompt, max_tasks)
        
        job = db.get_ai_job(job_id)
        if job:
            if job.status == AIJobStatus.COMPLETED:
                return {
                    "success": True,
                    "tasks_created": len(job.result) if job.result else 0,
                    "tasks": job.result
                }
            else:
                return {
                    "success": False,
                    "error": job.error
                }
        else:
            return {"success": False, "error": "作业未找到"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}

# ===== 通用路由 =====
@general_router.get("/stats", response_model=TaskStatsResponse)
async def get_stats():
    """获取任务统计信息"""
    return TaskService.get_task_stats()

@general_router.get("/tags", response_model=TagsResponse)
async def get_available_tags():
    """获取所有可用的标签"""
    return TagService.get_available_tags()
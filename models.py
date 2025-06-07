"""
数据模型定义
"""
from pydantic import BaseModel
from typing import List, Optional, Dict, Union, Any
from datetime import datetime, date
from enum import Enum

# ===== 枚举定义 =====
class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

class AIJobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskTag(str, Enum):
    TODAY = "今日"
    TOMORROW = "明日"
    IMPORTANT = "重要"
    URGENT = "紧急"
    COMPLETED = "已完成"
    OVERDUE = "已过期"
    WORK = "工作"
    PERSONAL = "个人"
    LEARNING = "学习"
    PROJECT = "项目"

# ===== 任务相关模型 =====
class Task(BaseModel):
    id: Optional[str] = None
    name: str
    description: Optional[str] = ""
    completed: bool = False
    status: TaskStatus = TaskStatus.PENDING
    created_at: Optional[datetime] = None
    due_date: Optional[datetime] = None
    priority: Optional[str] = "medium"  # low, medium, high
    estimated_hours: Optional[float] = None
    scheduled_date: Optional[date] = None
    tags: Optional[List[str]] = []  # 保留原有tags字段
    task_tags: Optional[List[str]] = []  # 多标签系统
    original_tags: Optional[List[str]] = []  # 保存原始标签

class TaskCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    due_date: Optional[datetime] = None
    priority: Optional[str] = "medium"
    estimated_hours: Optional[float] = None
    scheduled_date: Optional[date] = None
    tags: Optional[List[str]] = []
    task_tags: Optional[List[str]] = []

class TaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None
    status: Optional[TaskStatus] = None
    due_date: Optional[datetime] = None
    priority: Optional[str] = None
    estimated_hours: Optional[float] = None
    scheduled_date: Optional[date] = None
    tags: Optional[List[str]] = None
    task_tags: Optional[List[str]] = None

# ===== AI相关模型 =====
class AITaskRequest(BaseModel):
    prompt: str
    max_tasks: int = 5

class AIScheduleRequest(BaseModel):
    task_ids: Optional[List[str]] = None

class AIDayScheduleRequest(BaseModel):
    date: str  # YYYY-MM-DD 格式
    task_ids: Optional[List[str]] = None

class TaskScheduleItem(BaseModel):
    task_id: str
    task_name: str
    start_time: str  # HH:MM 格式
    end_time: str    # HH:MM 格式
    duration: float  # 小时
    priority: str
    reason: str      # AI安排的原因

class DaySchedule(BaseModel):
    id: Optional[str] = None
    date: date
    created_at: datetime
    updated_at: datetime
    schedule_items: List[TaskScheduleItem]
    suggestions: List[str]
    total_hours: float
    efficiency_score: int
    task_version: str

class DayScheduleResponse(BaseModel):
    date: str
    has_schedule: bool
    schedule: Optional[DaySchedule] = None
    tasks_changed: bool = False

class AIJob(BaseModel):
    job_id: str
    status: AIJobStatus
    created_at: datetime
    result: Optional[Any] = None
    error: Optional[str] = None

# ===== 响应模型 =====
class TaskStatsResponse(BaseModel):
    total: int
    completed: int
    pending: int
    due_today: int
    overdue: int
    by_priority: Dict[str, int]
    by_status: Dict[str, int]
    by_tags: Dict[str, int]

class TagsResponse(BaseModel):
    system_tags: List[str]
    tag_descriptions: Dict[str, str]
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Union, Any
from datetime import datetime, date, timedelta
import uuid
import json
from enum import Enum
from openai import OpenAI

app = FastAPI()

# 配置跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 配置 OpenAI
client = OpenAI(
    api_key="sk-zmyrpclntmuvmufqjclmjczurrexkvzsfcrxthcwzgyffktd",
    base_url="https://api.siliconflow.cn/v1",
)

# ===== 枚举和常量 =====
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
    COMPLETED = "已完成"
    OVERDUE = "已过期"

# ===== 数据模型 =====
class Task(BaseModel):
    id: Optional[str] = None
    name: str
    description: Optional[str] = ""
    completed: bool = False
    status: TaskStatus = TaskStatus.PENDING
    created_at: Optional[datetime] = None
    due_date: Optional[datetime] = None
    priority: Optional[str] = "medium"  # low, medium, high
    estimated_hours: Optional[float] = None  # 预计所需小时数
    scheduled_date: Optional[date] = None  # 计划执行日期
    tags: Optional[List[str]] = []
    task_tag: Optional[str] = TaskTag.TODAY  # 新增的任务标签
    original_tag: Optional[str] = None  # 新增：保存原始标签，用于取消完成时恢复

class TaskCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    due_date: Optional[datetime] = None
    priority: Optional[str] = "medium"
    estimated_hours: Optional[float] = None
    scheduled_date: Optional[date] = None
    tags: Optional[List[str]] = []
    task_tag: Optional[str] = TaskTag.TODAY

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
    task_tag: Optional[str] = None

class AITaskRequest(BaseModel):
    prompt: str
    max_tasks: int = 3  # 限制生成任务数量

class AIScheduleRequest(BaseModel):
    task_ids: Optional[List[str]] = None  # 如果为空，则规划所有未完成任务

# AI日程安排相关模型
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
    date: date  # 安排的日期
    created_at: datetime  # 创建时间
    updated_at: datetime  # 更新时间
    schedule_items: List[TaskScheduleItem]  # 安排的任务列表
    suggestions: List[str]  # AI建议
    total_hours: float  # 总工作时长
    efficiency_score: int  # 效率评分
    task_version: str  # 任务版本号（用于检测任务变化）

class DayScheduleResponse(BaseModel):
    date: str
    has_schedule: bool  # 是否已有安排
    schedule: Optional[DaySchedule] = None
    tasks_changed: bool = False  # 任务是否发生变化

class AIJob(BaseModel):
    job_id: str
    status: AIJobStatus
    created_at: datetime
    result: Optional[Any] = None  # 使用Any类型支持不同格式的结果
    error: Optional[str] = None

# ===== 内存存储 =====
tasks_db: Dict[str, Task] = {}
ai_jobs_db: Dict[str, AIJob] = {}
day_schedules_db: Dict[str, DaySchedule] = {}  # key: "YYYY-MM-DD"

# ===== 辅助函数 =====
def auto_assign_task_tag(task: Task) -> str:
    """根据任务状态自动分配标签"""
    now = datetime.now()
    today = now.date()
    tomorrow = today + timedelta(days=1)
    
    # 如果任务已完成
    if task.completed:
        return TaskTag.COMPLETED
    
    # 如果任务已过期
    if task.due_date and task.due_date.date() < today:
        return TaskTag.OVERDUE
    
    # 如果是高优先级
    if task.priority == "high":
        return TaskTag.IMPORTANT
    
    # 如果明天到期
    if task.due_date and task.due_date.date() == tomorrow:
        return TaskTag.TOMORROW
    
    # 默认为今日
    return TaskTag.TODAY

def update_task_tag(task: Task):
    """更新任务标签，保留原始标签用于恢复"""
    # 如果任务刚刚完成
    if task.completed and task.task_tag != TaskTag.COMPLETED:
        # 保存当前标签作为原始标签
        if not task.original_tag:
            task.original_tag = task.task_tag
        # 设置为已完成
        task.task_tag = TaskTag.COMPLETED
    
    # 如果任务从完成状态变为未完成
    elif not task.completed and task.task_tag == TaskTag.COMPLETED:
        # 如果有原始标签，恢复到原始标签
        if task.original_tag:
            task.task_tag = task.original_tag
            # 清除原始标签记录
            task.original_tag = None
        else:
            # 如果没有原始标签，重新自动分配
            task.task_tag = auto_assign_task_tag(task)
    
    # 如果任务没有完成，且不是从完成状态恢复，则自动更新标签
    elif not task.completed and task.task_tag != TaskTag.COMPLETED:
        # 只有当用户没有手动设置特殊标签时才自动更新
        current_auto_tag = auto_assign_task_tag(task)
        
        # 如果当前标签是系统自动分配的类型，则更新
        if task.task_tag in [TaskTag.TODAY, TaskTag.TOMORROW, TaskTag.OVERDUE]:
            task.task_tag = current_auto_tag
        # 如果是用户手动设置的重要标签，且不冲突，则保持
        elif task.task_tag == TaskTag.IMPORTANT and task.priority == "high":
            pass  # 保持重要标签
        # 其他情况下，如果任务已过期，强制更新为过期
        elif current_auto_tag == TaskTag.OVERDUE:
            if not task.original_tag:
                task.original_tag = task.task_tag
            task.task_tag = TaskTag.OVERDUE

# 生成任务版本号（用于检测任务变化）
def generate_task_version(tasks: List[Task]) -> str:
    """根据任务列表生成版本号，用于检测任务是否发生变化"""
    import hashlib
    
    # 将任务的关键信息组合成字符串
    task_info = []
    for task in sorted(tasks, key=lambda t: t.id):
        info = f"{task.id}:{task.name}:{task.completed}:{task.priority}:{task.due_date}:{task.estimated_hours}"
        task_info.append(info)
    
    # 生成哈希值作为版本号
    version_string = "|".join(task_info)
    return hashlib.md5(version_string.encode()).hexdigest()

# 获取指定日期的任务列表
def get_tasks_for_date(target_date: date) -> List[Task]:
    """获取指定日期的任务"""
    tasks_for_date = []
    
    for task in tasks_db.values():
        if task.completed:
            continue
            
        is_target_date_task = False
        
        # 截止日期在目标日期
        if task.due_date and task.due_date.date() == target_date:
            is_target_date_task = True
        
        # 计划日期在目标日期
        if task.scheduled_date and task.scheduled_date == target_date:
            is_target_date_task = True
        
        if is_target_date_task:
            update_task_tag(task)
            tasks_for_date.append(task)
    
    return tasks_for_date

# ===== 基础任务操作 =====
@app.post("/tasks", response_model=Task)
async def create_task(task: TaskCreate):
    """创建新任务"""
    new_task = Task(
        id=str(uuid.uuid4()),
        name=task.name,
        description=task.description,
        created_at=datetime.now(),
        due_date=task.due_date,
        priority=task.priority,
        estimated_hours=task.estimated_hours,
        scheduled_date=task.scheduled_date,
        tags=task.tags,
        task_tag=task.task_tag or TaskTag.TODAY,
        original_tag=None,  # 新任务没有原始标签
    )
    
    # 自动分配标签
    update_task_tag(new_task)
    
    tasks_db[new_task.id] = new_task
    return new_task

@app.get("/tasks", response_model=List[Task])
async def get_all_tasks():
    """获取所有任务"""
    # 更新所有任务的标签
    for task in tasks_db.values():
        update_task_tag(task)
    return list(tasks_db.values())

@app.get("/tasks/{task_id}", response_model=Task)
async def get_task(task_id: str):
    """获取单个任务"""
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = tasks_db[task_id]
    update_task_tag(task)
    return task

@app.put("/tasks/{task_id}", response_model=Task)
async def update_task(task_id: str, task_update: TaskUpdate):
    """更新任务"""
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="任务不存在")

    task = tasks_db[task_id]
    
    # 记录更新前的状态
    was_completed = task.completed
    
    # 应用更新
    update_data = task_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)

    # 如果完成状态发生变化，更新相关状态
    if task.completed != was_completed:
        if task.completed:
            # 任务被标记为完成
            task.status = TaskStatus.COMPLETED
        else:
            # 任务被取消完成
            task.status = TaskStatus.PENDING

    # 更新任务标签（这里会处理完成/取消完成的标签逻辑）
    update_task_tag(task)

    return task

@app.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    """删除任务"""
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="任务不存在")
    del tasks_db[task_id]
    return {"message": "任务已删除"}

# ===== 日历视图 =====
@app.get("/tasks/calendar/{year}/{month}")
async def get_calendar_tasks(year: int, month: int):
    """获取指定月份的任务日历数据"""
    calendar_data = {}
    
    for task in tasks_db.values():
        if task.completed:
            continue
            
        # 更新任务标签
        update_task_tag(task)
            
        # 检查截止日期
        if task.due_date:
            due_date = task.due_date.date()
            if due_date.year == year and due_date.month == month:
                date_str = due_date.isoformat()
                if date_str not in calendar_data:
                    calendar_data[date_str] = {"due": [], "scheduled": []}
                calendar_data[date_str]["due"].append(task)
        
        # 检查计划日期
        if task.scheduled_date:
            if task.scheduled_date.year == year and task.scheduled_date.month == month:
                date_str = task.scheduled_date.isoformat()
                if date_str not in calendar_data:
                    calendar_data[date_str] = {"due": [], "scheduled": []}
                calendar_data[date_str]["scheduled"].append(task)
    
    return calendar_data

# ===== 按标签获取任务 =====
@app.get("/tasks/by-tag/{tag}")
async def get_tasks_by_tag(tag: str):
    """根据标签获取任务"""
    if tag not in [TaskTag.TODAY, TaskTag.TOMORROW, TaskTag.IMPORTANT, TaskTag.COMPLETED, TaskTag.OVERDUE]:
        raise HTTPException(status_code=400, detail="无效的标签")
    
    # 更新所有任务的标签
    for task in tasks_db.values():
        update_task_tag(task)
    
    filtered_tasks = [task for task in tasks_db.values() if task.task_tag == tag]
    return filtered_tasks

# ===== AI日程安排处理 =====
async def process_ai_day_schedule(job_id: str, date_str: str, task_ids: Optional[List[str]] = None, force_regenerate: bool = False):
    """后台处理AI日程安排，支持结果持久化"""
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        
        # 获取指定日期的任务
        if task_ids:
            tasks_to_schedule = []
            for task_id in task_ids:
                if task_id in tasks_db and not tasks_db[task_id].completed:
                    tasks_to_schedule.append(tasks_db[task_id])
        else:
            tasks_to_schedule = get_tasks_for_date(target_date)
        
        if not tasks_to_schedule:
            # 保存空的安排结果
            empty_schedule = DaySchedule(
                id=str(uuid.uuid4()),
                date=target_date,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                schedule_items=[],
                suggestions=["今天没有安排任务，可以休息或处理其他事务"],
                total_hours=0,
                efficiency_score=10,
                task_version=""
            )
            day_schedules_db[date_str] = empty_schedule
            
            ai_jobs_db[job_id].status = AIJobStatus.COMPLETED
            ai_jobs_db[job_id].result = {
                "date": date_str,
                "has_schedule": True,
                "schedule": empty_schedule.dict(),
                "tasks_changed": False
            }
            return
        
        # 生成当前任务版本号
        current_task_version = generate_task_version(tasks_to_schedule)
        
        # 检查是否已有安排且任务未变化
        if not force_regenerate and date_str in day_schedules_db:
            existing_schedule = day_schedules_db[date_str]
            if existing_schedule.task_version == current_task_version:
                # 任务没有变化，直接返回现有安排
                ai_jobs_db[job_id].status = AIJobStatus.COMPLETED
                ai_jobs_db[job_id].result = {
                    "date": date_str,
                    "has_schedule": True,
                    "schedule": existing_schedule.dict(),
                    "tasks_changed": False
                }
                return
        
        # 准备任务信息供AI分析
        tasks_info = []
        for task in tasks_to_schedule:
            task_info = {
                "id": task.id,
                "name": task.name,
                "description": task.description or "",
                "priority": task.priority,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "estimated_hours": task.estimated_hours or 2.0,
                "task_tag": task.task_tag,
                "is_overdue": task.due_date and task.due_date < datetime.now() if task.due_date else False
            }
            tasks_info.append(task_info)
        
        # AI处理逻辑
        now = datetime.now()
        weekday_names = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        target_weekday = weekday_names[target_date.weekday()]
        
        response = client.chat.completions.create(
            model="Qwen/Qwen2.5-7B-Instruct",
            messages=[
                {
                    "role": "system",
                    "content": f"""你是一个专业的时间管理和日程安排助手。请为用户安排 {date_str}({target_weekday}) 的任务时间表。
                    
                    当前时间：{now.strftime("%Y-%m-%d %H:%M")}
                    安排日期：{date_str} {target_weekday}
                    
                    安排原则：
                    1. 工作时间：9:00-18:00 为主要工作时间，18:00-22:00 为灵活时间
                    2. 优先级：高优先级任务优先安排在上午精力充沛时段
                    3. 截止时间：临近截止的任务优先安排
                    4. 任务时长：根据预计时长合理分配，避免过度紧凑
                    5. 休息时间：任务间预留15-30分钟休息
                    6. 逾期任务：已逾期任务最优先处理
                    
                    请返回JSON格式：
                    {{
                        "schedule": [
                            {{
                                "task_id": "任务ID",
                                "start_time": "09:00",
                                "end_time": "11:00", 
                                "reason": "安排原因说明"
                            }}
                        ],
                        "suggestions": ["建议1", "建议2"],
                        "efficiency_score": 8
                    }}
                    """,
                },
                {
                    "role": "user", 
                    "content": f"请为以下任务安排时间：\n{json.dumps(tasks_info, ensure_ascii=False, indent=2)}"
                },
            ],
            temperature=0.7,
            max_tokens=800,
        )
        
        # 解析AI响应
        content = response.choices[0].message.content
        start_idx = content.find('{')
        end_idx = content.rfind('}') + 1
        if start_idx != -1 and end_idx > start_idx:
            json_content = content[start_idx:end_idx]
            ai_result = json.loads(json_content)
        else:
            ai_result = json.loads(content)
        
        # 构建详细的日程安排
        schedule_items = []
        total_hours = 0
        
        for item in ai_result.get("schedule", []):
            task_id = item["task_id"]
            if task_id in tasks_db:
                task = tasks_db[task_id]
                start_time = item["start_time"]
                end_time = item["end_time"]
                
                # 计算持续时间
                start_hour, start_min = map(int, start_time.split(':'))
                end_hour, end_min = map(int, end_time.split(':'))
                duration = (end_hour * 60 + end_min - start_hour * 60 - start_min) / 60
                total_hours += duration
                
                schedule_item = TaskScheduleItem(
                    task_id=task_id,
                    task_name=task.name,
                    start_time=start_time,
                    end_time=end_time,
                    duration=duration,
                    priority=task.priority,
                    reason=item.get("reason", "根据优先级和时长安排")
                )
                schedule_items.append(schedule_item)
        
        # 创建并保存日程安排
        day_schedule = DaySchedule(
            id=str(uuid.uuid4()),
            date=target_date,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            schedule_items=schedule_items,
            suggestions=ai_result.get("suggestions", []),
            total_hours=total_hours,
            efficiency_score=ai_result.get("efficiency_score", 8),
            task_version=current_task_version
        )
        
        # 保存到内存数据库
        day_schedules_db[date_str] = day_schedule
        
        # 保存AI作业结果
        ai_jobs_db[job_id].status = AIJobStatus.COMPLETED
        ai_jobs_db[job_id].result = {
            "date": date_str,
            "has_schedule": True,
            "schedule": day_schedule.dict(),
            "tasks_changed": False
        }
        
    except Exception as e:
        ai_jobs_db[job_id].status = AIJobStatus.FAILED
        ai_jobs_db[job_id].error = str(e)

# ===== AI相关API端点 =====
@app.post("/ai/schedule-day/async")
async def ai_schedule_day_async(request: AIDayScheduleRequest, background_tasks: BackgroundTasks, force_regenerate: bool = False):
    """异步AI日程安排"""
    job_id = str(uuid.uuid4())
    job = AIJob(
        job_id=job_id,
        status=AIJobStatus.PENDING,
        created_at=datetime.now()
    )
    ai_jobs_db[job_id] = job
    
    # 添加后台任务，支持强制重新生成
    background_tasks.add_task(process_ai_day_schedule, job_id, request.date, request.task_ids, force_regenerate)
    
    return {"job_id": job_id, "status": "processing"}

@app.get("/ai/schedule/{date}")
async def get_day_schedule(date: str):
    """获取指定日期的AI安排"""
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，请使用YYYY-MM-DD格式")
    
    # 检查是否有保存的安排
    if date in day_schedules_db:
        schedule = day_schedules_db[date]
        
        # 检查任务是否发生变化
        current_tasks = get_tasks_for_date(target_date)
        current_version = generate_task_version(current_tasks)
        tasks_changed = schedule.task_version != current_version
        
        return DayScheduleResponse(
            date=date,
            has_schedule=True,
            schedule=schedule,
            tasks_changed=tasks_changed
        )
    else:
        return DayScheduleResponse(
            date=date,
            has_schedule=False,
            schedule=None,
            tasks_changed=False
        )

@app.delete("/ai/schedule/{date}")
async def delete_day_schedule(date: str):
    """删除指定日期的AI安排"""
    if date in day_schedules_db:
        del day_schedules_db[date]
        return {"message": "安排已删除"}
    else:
        raise HTTPException(status_code=404, detail="该日期没有安排")

@app.get("/ai/schedule-day/{date}")
async def get_day_schedule_preview(date: str):
    """获取指定日期的任务预览（用于显示AI安排按钮前的信息）"""
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，请使用YYYY-MM-DD格式")
    
    # 收集该日期的任务
    day_tasks = get_tasks_for_date(target_date)
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
                "task_tag": task.task_tag
            }
            for task in day_tasks
        ]
    }

@app.get("/ai/jobs/{job_id}")
async def get_ai_job_status(job_id: str):
    """获取 AI 任务状态"""
    if job_id not in ai_jobs_db:
        raise HTTPException(status_code=404, detail="任务不存在")
    return ai_jobs_db[job_id]

# ===== 其他AI功能 =====
async def process_ai_planning(job_id: str, prompt: str, max_tasks: int):
    """后台处理 AI 任务规划"""
    try:
        # 获取当前时间信息
        now = datetime.now()
        current_date_str = now.strftime("%Y年%m月%d日 %H:%M")
        weekday_names = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        current_weekday = weekday_names[now.weekday()]
        
        response = client.chat.completions.create(
            model="Qwen/Qwen2.5-7B-Instruct",
            messages=[
                {
                    "role": "system",
                    "content": f"""你是一个任务规划助手。根据用户的描述，将其分解为具体的任务步骤。
                    
                    当前时间：{current_date_str} {current_weekday}
                    
                    限制：最多生成 {max_tasks} 个任务。
                    
                    每个任务应该包含：
                    - name: 任务名称（简短明确）
                    - description: 任务描述（详细说明）
                    - priority: 优先级（high/medium/low）
                    - estimated_hours: 预计所需小时数
                    - due_date: 截止时间（ISO格式，如：2024-12-25T15:00:00）
                    - task_tag: 任务标签（今日/明日/重要/已完成/已过期）
                    
                    重要规则：
                    1. 根据任务的紧急程度和依赖关系设置合理的截止时间
                    2. 如果用户提到"明天"、"后天"等相对时间，要转换为具体日期
                    3. 考虑任务的先后顺序，前置任务的截止时间要早于后续任务
                    4. 紧急任务设置为high优先级，截止时间更近，标签设为"重要"
                    5. 所有时间都基于当前时间计算
                    6. 根据截止时间合理设置task_tag：今天到期用"今日"，明天到期用"明日"，高优先级用"重要"
                    
                    请以JSON数组格式返回，确保返回的是有效的JSON。
                    """,
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=500,
        )

        # 解析 AI 返回的内容
        content = response.choices[0].message.content
        # 尝试提取 JSON 部分
        start_idx = content.find('[')
        end_idx = content.rfind(']') + 1
        if start_idx != -1 and end_idx > start_idx:
            json_content = content[start_idx:end_idx]
            ai_tasks = json.loads(json_content)
        else:
            ai_tasks = json.loads(content)

        # 限制任务数量
        ai_tasks = ai_tasks[:max_tasks]

        # 创建任务并保存
        created_tasks = []
        for task_data in ai_tasks:
            # 处理due_date，确保是有效的ISO格式
            due_date_str = task_data.get("due_date")
            due_date = None
            if due_date_str:
                try:
                    # 尝试解析AI返回的日期
                    due_date = datetime.fromisoformat(due_date_str.replace('Z', '+00:00'))
                except:
                    # 如果解析失败，尝试其他格式或使用默认值
                    try:
                        due_date = datetime.strptime(due_date_str, "%Y-%m-%dT%H:%M:%S")
                    except:
                        # 如果还是失败，根据优先级设置默认截止时间
                        if task_data.get("priority") == "high":
                            due_date = datetime.now() + timedelta(days=1)
                        elif task_data.get("priority") == "medium":
                            due_date = datetime.now() + timedelta(days=3)
                        else:
                            due_date = datetime.now() + timedelta(days=7)
            
            new_task = Task(
                id=str(uuid.uuid4()),
                name=task_data.get("name", "未命名任务"),
                description=task_data.get("description", ""),
                created_at=datetime.now(),
                priority=task_data.get("priority", "medium"),
                estimated_hours=task_data.get("estimated_hours"),
                due_date=due_date,
                task_tag=task_data.get("task_tag", TaskTag.TODAY),
            )
            
            # 自动分配标签
            update_task_tag(new_task)
            
            tasks_db[new_task.id] = new_task
            created_tasks.append(new_task)

        # 更新任务状态 - 返回字典格式保持兼容性
        ai_jobs_db[job_id].status = AIJobStatus.COMPLETED
        ai_jobs_db[job_id].result = [task.dict() for task in created_tasks]

    except Exception as e:
        ai_jobs_db[job_id].status = AIJobStatus.FAILED
        ai_jobs_db[job_id].error = str(e)

@app.post("/ai/plan-tasks/async")
async def ai_plan_tasks_async(request: AITaskRequest, background_tasks: BackgroundTasks):
    """异步 AI 任务规划"""
    job_id = str(uuid.uuid4())
    job = AIJob(
        job_id=job_id,
        status=AIJobStatus.PENDING,
        created_at=datetime.now()
    )
    ai_jobs_db[job_id] = job
    
    # 添加后台任务
    background_tasks.add_task(process_ai_planning, job_id, request.prompt, request.max_tasks)
    
    return {"job_id": job_id, "status": "processing"}

@app.post("/ai/schedule-tasks", response_model=Dict[str, List[Task]])
async def ai_schedule_tasks(request: AIScheduleRequest):
    """AI 根据优先级和截止日期智能安排任务"""
    # 获取需要规划的任务
    tasks_to_schedule = []
    if request.task_ids:
        for task_id in request.task_ids:
            if task_id in tasks_db and not tasks_db[task_id].completed:
                tasks_to_schedule.append(tasks_db[task_id])
    else:
        tasks_to_schedule = [t for t in tasks_db.values() if not t.completed]
    
    if not tasks_to_schedule:
        return {"today": [], "tomorrow": [], "this_week": [], "later": []}
    
    try:
        # 获取当前时间信息
        now = datetime.now()
        today = now.date()
        tomorrow = today + timedelta(days=1)
        week_end = today + timedelta(days=7)
        
        # 准备任务信息
        tasks_info = []
        for task in tasks_to_schedule:
            # 更新任务标签
            update_task_tag(task)
            
            task_info = {
                "id": task.id,
                "name": task.name,
                "priority": task.priority,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "estimated_hours": task.estimated_hours,
                "task_tag": task.task_tag,
                "is_overdue": task.due_date and task.due_date < now if task.due_date else False
            }
            tasks_info.append(task_info)
        
        response = client.chat.completions.create(
            model="Qwen/Qwen2.5-7B-Instruct",
            messages=[
                {
                    "role": "system",
                    "content": f"""你是一个任务时间规划助手。根据任务的优先级、截止日期和预计时长，
                    合理安排任务的执行时间。
                    
                    当前时间：{now.strftime("%Y-%m-%d %H:%M")}
                    今天：{today}
                    明天：{tomorrow}
                    本周结束：{week_end}
                    
                    将任务分配到以下时间段：
                    - today: 今天应该完成的任务（紧急或即将到期）
                    - tomorrow: 明天应该完成的任务
                    - this_week: 本周内应该完成的任务
                    - later: 之后再做的任务
                    
                    考虑因素：
                    1. 已过期的任务必须放在today
                    2. 高优先级任务优先安排
                    3. 截止日期临近的任务优先
                    4. 每天工作时间不超过8小时
                    5. 考虑任务的预计时长，合理分配
                    6. 参考任务的task_tag标签
                    
                    返回JSON格式：
                    {{
                        "today": ["task_id1", "task_id2"],
                        "tomorrow": ["task_id3"],
                        "this_week": ["task_id4"],
                        "later": ["task_id5"]
                    }}
                    """
                },
                {
                    "role": "user",
                    "content": f"请为以下任务安排执行时间：\n{json.dumps(tasks_info, ensure_ascii=False)}"
                }
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        # 解析响应
        content = response.choices[0].message.content
        # 提取JSON部分
        start_idx = content.find('{')
        end_idx = content.rfind('}') + 1
        if start_idx != -1 and end_idx > start_idx:
            json_content = content[start_idx:end_idx]
            schedule = json.loads(json_content)
        else:
            schedule = json.loads(content)
        
        # 构建返回结果
        result = {
            "today": [],
            "tomorrow": [],
            "this_week": [],
            "later": []
        }
        
        for period, task_ids in schedule.items():
            if period in result:
                for task_id in task_ids:
                    if task_id in tasks_db:
                        result[period].append(tasks_db[task_id])
        
        return result
        
    except Exception as e:
        # 如果AI失败，使用简单的规则进行调度
        result = {
            "today": [],
            "tomorrow": [],
            "this_week": [],
            "later": []
        }
        
        # 按优先级和截止日期排序
        sorted_tasks = sorted(tasks_to_schedule, 
                            key=lambda t: (
                                t.priority != "high",  # 高优先级优先
                                t.due_date or datetime.max,  # 有截止日期的优先
                                t.created_at
                            ))
        
        today_hours = 0
        tomorrow_hours = 0
        
        for task in sorted_tasks:
            task_hours = task.estimated_hours or 2  # 默认2小时
            
            # 已过期或今天到期的任务
            if task.due_date and task.due_date.date() <= today:
                result["today"].append(task)
                today_hours += task_hours
            # 明天到期的任务
            elif task.due_date and task.due_date.date() == tomorrow:
                result["tomorrow"].append(task)
                tomorrow_hours += task_hours
            # 本周内到期的任务
            elif task.due_date and task.due_date.date() <= week_end:
                result["this_week"].append(task)
            # 根据工作负荷分配
            elif today_hours < 8:
                result["today"].append(task)
                today_hours += task_hours
            elif tomorrow_hours < 8:
                result["tomorrow"].append(task)
                tomorrow_hours += task_hours
            else:
                result["later"].append(task)
        
        return result

# ===== 统计信息 =====
@app.get("/stats")
async def get_stats():
    """获取任务统计信息"""
    all_tasks = list(tasks_db.values())
    
    # 更新所有任务的标签
    for task in all_tasks:
        update_task_tag(task)
    
    completed = sum(1 for t in all_tasks if t.completed)
    
    # 计算今日到期任务
    today = date.today()
    due_today = sum(1 for t in all_tasks 
                    if t.due_date and t.due_date.date() == today and not t.completed)
    
    # 计算逾期任务
    overdue = sum(1 for t in all_tasks 
                  if t.due_date and t.due_date.date() < today and not t.completed)

    return {
        "total": len(all_tasks),
        "completed": completed,
        "pending": len(all_tasks) - completed,
        "due_today": due_today,
        "overdue": overdue,
        "by_priority": {
            "high": sum(1 for t in all_tasks if t.priority == "high" and not t.completed),
            "medium": sum(1 for t in all_tasks if t.priority == "medium" and not t.completed),
            "low": sum(1 for t in all_tasks if t.priority == "low" and not t.completed),
        },
        "by_status": {
            "pending": sum(1 for t in all_tasks if t.status == TaskStatus.PENDING),
            "in_progress": sum(1 for t in all_tasks if t.status == TaskStatus.IN_PROGRESS),
            "completed": sum(1 for t in all_tasks if t.status == TaskStatus.COMPLETED),
        },
        "by_tag": {
            "today": sum(1 for t in all_tasks if t.task_tag == TaskTag.TODAY),
            "tomorrow": sum(1 for t in all_tasks if t.task_tag == TaskTag.TOMORROW),
            "important": sum(1 for t in all_tasks if t.task_tag == TaskTag.IMPORTANT),
            "completed": sum(1 for t in all_tasks if t.task_tag == TaskTag.COMPLETED),
            "overdue": sum(1 for t in all_tasks if t.task_tag == TaskTag.OVERDUE),
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
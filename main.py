from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime, date
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

class TaskCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    due_date: Optional[datetime] = None
    priority: Optional[str] = "medium"
    estimated_hours: Optional[float] = None
    scheduled_date: Optional[date] = None
    tags: Optional[List[str]] = []

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

class AITaskRequest(BaseModel):
    prompt: str
    max_tasks: int = 3  # 限制生成任务数量

class AIScheduleRequest(BaseModel):
    task_ids: Optional[List[str]] = None  # 如果为空，则规划所有未完成任务

class AIJob(BaseModel):
    job_id: str
    status: AIJobStatus
    created_at: datetime
    result: Optional[List[Task]] = None
    error: Optional[str] = None

# ===== 内存存储 =====
tasks_db: Dict[str, Task] = {}
ai_jobs_db: Dict[str, AIJob] = {}

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
    )
    tasks_db[new_task.id] = new_task
    return new_task

@app.get("/tasks", response_model=List[Task])
async def get_all_tasks():
    """获取所有任务"""
    return list(tasks_db.values())

@app.get("/tasks/{task_id}", response_model=Task)
async def get_task(task_id: str):
    """获取单个任务"""
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="任务不存在")
    return tasks_db[task_id]

@app.put("/tasks/{task_id}", response_model=Task)
async def update_task(task_id: str, task_update: TaskUpdate):
    """更新任务"""
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="任务不存在")

    task = tasks_db[task_id]
    update_data = task_update.dict(exclude_unset=True)

    for field, value in update_data.items():
        setattr(task, field, value)

    # 如果标记为完成，自动更新状态
    if task.completed and task.status != TaskStatus.COMPLETED:
        task.status = TaskStatus.COMPLETED

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

# ===== 异步 AI 功能 =====
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
                    
                    重要规则：
                    1. 根据任务的紧急程度和依赖关系设置合理的截止时间
                    2. 如果用户提到"明天"、"后天"等相对时间，要转换为具体日期
                    3. 考虑任务的先后顺序，前置任务的截止时间要早于后续任务
                    4. 紧急任务设置为high优先级，截止时间更近
                    5. 所有时间都基于当前时间计算
                    
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
            )
            tasks_db[new_task.id] = new_task
            created_tasks.append(new_task)

        # 更新任务状态
        ai_jobs_db[job_id].status = AIJobStatus.COMPLETED
        ai_jobs_db[job_id].result = created_tasks

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

@app.get("/ai/jobs/{job_id}")
async def get_ai_job_status(job_id: str):
    """获取 AI 任务状态"""
    if job_id not in ai_jobs_db:
        raise HTTPException(status_code=404, detail="任务不存在")
    return ai_jobs_db[job_id]

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
            task_info = {
                "id": task.id,
                "name": task.name,
                "priority": task.priority,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "estimated_hours": task.estimated_hours,
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
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
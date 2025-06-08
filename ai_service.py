"""
AI服务模块 - 简化标签系统后的版本
"""
import json
import uuid
from typing import List, Dict, Any
from datetime import datetime, timedelta
from openai import OpenAI

from models import Task, AIJob, AIJobStatus, DaySchedule, TaskScheduleItem
from database import db
from tag_service import TagService

# 配置 OpenAI 客户端
client = OpenAI(
    api_key="sk-zmyrpclntmuvmufqjclmjczurrexkvzsfcrxthcwzgyffktd",
    base_url="https://api.siliconflow.cn/v1",
)

class AIService:
    @staticmethod
    async def process_task_planning(job_id: str, prompt: str, max_tasks: int):
        """后台处理 AI 任务规划"""
        try:
            # 获取当前时间信息
            now = datetime.now()
            current_date_str = now.strftime("%Y年%m月%d日 %H:%M")
            weekday_names = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
            current_weekday = weekday_names[now.weekday()]
            
            # 分析任务类型
            task_type = AIService._analyze_task_type(prompt)
            current_guidance = AIService._get_type_specific_guidance(task_type)
            
            response = client.chat.completions.create(
                model="Qwen/Qwen2.5-7B-Instruct",
                messages=[
                    {
                        "role": "system",
                        "content": f"""你是一个专业的任务分解和项目管理专家。你需要为用户的目标生成一个项目主题和具体的子任务。

当前时间：{current_date_str} {current_weekday}
任务数量限制：严格生成 {max_tasks} 个任务（不多不少）
识别的任务类型：{task_type}

{current_guidance}

**输出格式要求**：
请按以下JSON格式返回，包含一个项目主题和任务列表：
```json
{{
  "project_theme": "项目主题名称（5-15字）",
  "tasks": [
    {{
      "name": "具体的子任务名称",
      "description": "详细的执行步骤和交付物描述",
      "priority": "high/medium/low",
      "estimated_hours": 2.0,
      "due_date": "2024-12-25T18:00:00"
    }}
  ]
}}
```

**项目主题要求**：
- 5-15字的简洁描述
- 概括整个目标的核心内容
- 便于用户快速识别项目范围

**子任务命名规则**：
- 每个子任务名称要具体明确
- 不需要包含step序号（系统会自动添加）
- 使用动词开头，描述具体行动

**核心原则**：
1. 具体性：每个任务都必须是具体的行动
2. 可执行性：任务描述要详细到任何人都能理解如何开始
3. 可衡量性：必须有明确的完成标准
4. 时间合理性：单个任务建议在0.5-6小时内完成
5. 逻辑顺序：任务间要有合理的先后顺序
6. 行动导向：每个任务名称必须以动词开头

**关键要求**：
1. 每个任务必须包含具体数字（时间、数量、频率）
2. 必须指定执行时间段（如：每天7:00-7:20）
3. 必须包含每日具体目标和衡量标准

**特殊任务处理**：
- 健身类：指定动作名称、组数、次数、持续时间
- 学习类：指定每日学习量、使用工具、复习计划
- 技能类：指定练习内容、时长、评估标准

**示例对比**：
❌ 错误示例："加强体能训练" 
✅ 正确示例："每天早上7:00-7:15进行15分钟卷腹训练，完成3组，每组20个"

❌ 错误示例："学习法语词汇"
✅ 正确示例："每天晚上20:00-20:30背诵30个法语单词，使用Anki软件复习"

请生成严格符合以上要求的项目主题和 {max_tasks} 个子任务。""",
                    },
                    {"role": "user", "content": f"请为以下目标生成项目主题和分解任务：{prompt}"},
                ],
                temperature=0.6,
                max_tokens=1500,
            )

            # 解析 AI 返回的内容
            content = response.choices[0].message.content
            print(f"AI原始返回内容: {content[:200]}...")
            
            ai_result = AIService._parse_ai_response(content, max_tasks)
            
            # 提取项目主题和任务列表
            project_theme = ai_result.get("project_theme", "AI规划项目")
            ai_tasks = ai_result.get("tasks", [])
            
            if len(ai_tasks) == 0:
                raise Exception("AI未能生成有效的任务列表")

            # 创建任务
            created_tasks = AIService._create_tasks_from_ai_result(
                ai_tasks, project_theme, max_tasks, now
            )

            # 更新AI作业状态
            job = db.get_ai_job(job_id)
            job.status = AIJobStatus.COMPLETED
            job.result = [task.dict() for task in created_tasks]
            db.update_ai_job(job_id, job)
            
            print(f"✅ AI任务规划完成")
            print(f"   项目主题: {project_theme}")
            print(f"   生成任务: {len(created_tasks)} 个")

        except Exception as e:
            error_msg = f"AI任务规划失败: {str(e)}"
            print(error_msg)
            job = db.get_ai_job(job_id)
            job.status = AIJobStatus.FAILED
            job.error = error_msg
            db.update_ai_job(job_id, job)

    @staticmethod
    def _analyze_task_type(prompt: str) -> str:
        """分析任务类型"""
        prompt_analysis = prompt.lower()
        
        if any(keyword in prompt_analysis for keyword in ["学习", "掌握", "了解", "研究"]):
            return "learning"
        elif any(keyword in prompt_analysis for keyword in ["开发", "编程", "制作", "创建", "设计"]):
            return "development"
        elif any(keyword in prompt_analysis for keyword in ["准备", "策划", "组织", "安排"]):
            return "planning"
        elif any(keyword in prompt_analysis for keyword in ["写", "撰写", "完成", "提交"]):
            return "writing"
        else:
            return "general"

    @staticmethod
    def _get_type_specific_guidance(task_type: str) -> str:
        """获取任务类型特定的指导原则"""
        type_specific_guidance = {
            "learning": """
**学习类任务特殊要求**：
- 将知识点分解为具体的学习单元
- 每个任务应包含明确的学习材料和练习
- 设置循序渐进的难度梯度
- 包含实践和验证环节""",
            
            "development": """
**开发类任务特殊要求**：
- 按照软件开发生命周期分解
- 每个任务应有明确的技术实现目标
- 包含测试和验证步骤
- 考虑技术依赖关系""",
            
            "planning": """
**策划类任务特殊要求**：
- 按照项目管理流程分解
- 包含调研、准备、执行、总结阶段
- 每个任务应有具体的交付物
- 考虑资源和时间约束""",
            
            "writing": """
**写作类任务特殊要求**：
- 按照写作流程分解（构思-大纲-初稿-修改-定稿）
- 每个任务应有明确的字数或篇幅目标
- 包含研究和素材收集环节
- 设置审核和优化步骤"""
        }
        
        return type_specific_guidance.get(task_type, "")

    @staticmethod
    def _parse_ai_response(content: str, max_tasks: int) -> dict:
        """解析AI响应内容"""
        # 尝试提取 JSON 部分
        start_idx = content.find('{')
        end_idx = content.rfind('}') + 1
        if start_idx != -1 and end_idx > start_idx:
            json_content = content[start_idx:end_idx]
            ai_result = json.loads(json_content)
        else:
            # 如果没有找到完整JSON，尝试解析为数组格式（兼容旧格式）
            start_idx = content.find('[')
            end_idx = content.rfind(']') + 1
            if start_idx != -1 and end_idx > start_idx:
                json_content = content[start_idx:end_idx]
                ai_tasks = json.loads(json_content)
                ai_result = {"project_theme": f"AI规划项目", "tasks": ai_tasks}
            else:
                raise Exception("无法解析AI返回的JSON格式")
        
        return ai_result

    @staticmethod
    def _create_tasks_from_ai_result(ai_tasks: List[dict], project_theme: str, max_tasks: int, base_time: datetime) -> List[Task]:
        """从AI结果创建任务"""
        # 严格限制任务数量
        ai_tasks = ai_tasks[:max_tasks]
        
        created_tasks = []
        
        for i, task_data in enumerate(ai_tasks):
            try:
                # 验证必需字段
                if not task_data.get("name"):
                    task_data["name"] = f"执行步骤{i+1}：相关任务"
                
                # 生成带主题和步骤的任务名称
                original_name = task_data.get("name", "").strip()
                
                # 确保名称以动词开头
                action_verbs = ["创建", "编写", "设计", "调研", "实现", "测试", "整理", "分析", "学习", "准备", "完成", "制作", "搭建", "配置", "安装"]
                if not any(original_name.startswith(verb) for verb in action_verbs):
                    original_name = f"完成{original_name}"
                
                # 构建最终的任务名称
                task_name = f"{project_theme} Step{i+1}：{original_name}"
                
                # 处理其他字段
                description = task_data.get("description", "").strip()
                if len(description) < 30:
                    description = f"具体执行：{description}。请根据实际情况制定详细的执行计划和验收标准。"
                
                priority = task_data.get("priority", "medium")
                if priority not in ["high", "medium", "low"]:
                    priority = "medium"
                
                # 设置截止时间
                if priority == "high" or i == 0:
                    days_offset = 1 + i * 0.5
                elif priority == "medium":
                    days_offset = 2 + i * 1.5
                else:
                    days_offset = 4 + i * 2
                
                due_date = base_time + timedelta(days=days_offset)
                due_date = due_date.replace(hour=18, minute=0, second=0, microsecond=0)
                
                # 验证预估时间
                estimated_hours = task_data.get("estimated_hours", 2.0)
                if isinstance(estimated_hours, str):
                    try:
                        estimated_hours = float(estimated_hours)
                    except:
                        estimated_hours = 2.0
                
                estimated_hours = max(0.5, min(6.0, float(estimated_hours)))
                
                # 创建任务对象（不再需要标签相关字段）
                new_task = Task(
                    id=str(uuid.uuid4()),
                    name=task_name,
                    description=description,
                    created_at=datetime.now(),
                    priority=priority,
                    estimated_hours=estimated_hours,
                    due_date=due_date,
                )
                
                # 保存到数据库
                db.create_task(new_task)
                created_tasks.append(new_task)
                
                print(f"创建任务 {i+1}/{max_tasks}: {new_task.name}")
                
            except Exception as task_error:
                print(f"处理任务 {i+1} 时出错: {task_error}")
                # 创建一个基础任务作为后备
                fallback_task = Task(
                    id=str(uuid.uuid4()),
                    name=f"{project_theme} Step{i+1}：完成目标的第{i+1}个步骤",
                    description=f"根据目标，完成相应的第{i+1}个具体行动步骤。请细化具体的执行方案。",
                    created_at=datetime.now(),
                    priority="medium",
                    estimated_hours=2.0,
                    due_date=base_time + timedelta(days=i+1, hours=18),
                )
                db.create_task(fallback_task)
                created_tasks.append(fallback_task)

        return created_tasks

    @staticmethod
    async def process_day_schedule(job_id: str, date_str: str, task_ids: List[str] = None, force_regenerate: bool = False):
        """后台处理AI日程安排"""
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            
            # 获取指定日期的任务
            if task_ids:
                tasks_to_schedule = []
                for task_id in task_ids:
                    task = db.get_task(task_id)
                    if task and not task.completed:
                        tasks_to_schedule.append(task)
            else:
                tasks_to_schedule = db.get_tasks_for_date(target_date)
            
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
                db.create_day_schedule(date_str, empty_schedule)
                
                job = db.get_ai_job(job_id)
                job.status = AIJobStatus.COMPLETED
                job.result = {
                    "date": date_str,
                    "has_schedule": True,
                    "schedule": empty_schedule.dict(),
                    "tasks_changed": False
                }
                db.update_ai_job(job_id, job)
                return
            
            # 生成当前任务版本号
            current_task_version = AIService._generate_task_version(tasks_to_schedule)
            
            # 检查是否已有安排且任务未变化
            if not force_regenerate:
                existing_schedule = db.get_day_schedule(date_str)
                if existing_schedule and existing_schedule.task_version == current_task_version:
                    job = db.get_ai_job(job_id)
                    job.status = AIJobStatus.COMPLETED
                    job.result = {
                        "date": date_str,
                        "has_schedule": True,
                        "schedule": existing_schedule.dict(),
                        "tasks_changed": False
                    }
                    db.update_ai_job(job_id, job)
                    return
            
            # AI处理日程安排
            schedule_result = await AIService._generate_day_schedule(tasks_to_schedule, target_date)
            
            # 创建并保存日程安排
            day_schedule = DaySchedule(
                id=str(uuid.uuid4()),
                date=target_date,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                schedule_items=schedule_result["schedule_items"],
                suggestions=schedule_result["suggestions"],
                total_hours=schedule_result["total_hours"],
                efficiency_score=schedule_result["efficiency_score"],
                task_version=current_task_version
            )
            
            db.create_day_schedule(date_str, day_schedule)
            
            # 保存AI作业结果
            job = db.get_ai_job(job_id)
            job.status = AIJobStatus.COMPLETED
            job.result = {
                "date": date_str,
                "has_schedule": True,
                "schedule": day_schedule.dict(),
                "tasks_changed": False
            }
            db.update_ai_job(job_id, job)
            
        except Exception as e:
            job = db.get_ai_job(job_id)
            job.status = AIJobStatus.FAILED
            job.error = str(e)
            db.update_ai_job(job_id, job)

    @staticmethod
    def _generate_task_version(tasks: List[Task]) -> str:
        """根据任务列表生成版本号"""
        import hashlib
        
        task_info = []
        for task in sorted(tasks, key=lambda t: t.id):
            info = f"{task.id}:{task.name}:{task.completed}:{task.priority}:{task.due_date}:{task.estimated_hours}"
            task_info.append(info)
        
        version_string = "|".join(task_info)
        return hashlib.md5(version_string.encode()).hexdigest()

    @staticmethod
    async def _generate_day_schedule(tasks: List[Task], target_date) -> dict:
        """生成日程安排 - 修复版本"""
        # 准备任务信息供AI分析
        tasks_info = []
        for task in tasks:
            task_info = {
                "id": task.id,
                "name": task.name,
                "description": task.description or "",
                "priority": task.priority,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "estimated_hours": task.estimated_hours or 2.0,
                "is_overdue": task.due_date and task.due_date < datetime.now() if task.due_date else False
                # 修复：移除对 task_tags 的引用
                # "task_tags": task.task_tags or [],  # 删除这行
            }
            tasks_info.append(task_info)
        
        # AI处理逻辑保持不变...
        now = datetime.now()
        weekday_names = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        target_weekday = weekday_names[target_date.weekday()]
        
        response = client.chat.completions.create(
            model="Qwen/Qwen2.5-7B-Instruct",
            messages=[
                {
                    "role": "system",
                    "content": f"""你是一个专业的时间管理和日程安排助手。请为用户安排 {target_date}({target_weekday}) 的任务时间表。
                    
                    当前时间：{now.strftime("%Y-%m-%d %H:%M")}
                    安排日期：{target_date} {target_weekday}
                    
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
            task = db.get_task(task_id)
            if task:
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
        
        return {
            "schedule_items": schedule_items,
            "suggestions": ai_result.get("suggestions", []),
            "total_hours": total_hours,
            "efficiency_score": ai_result.get("efficiency_score", 8)
        }
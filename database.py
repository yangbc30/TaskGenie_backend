"""
数据库操作模块
目前使用内存存储，后续可以替换为真实数据库
"""
from typing import Dict, List, Optional
from models import Task, AIJob, DaySchedule

# ===== 内存数据库 =====
class InMemoryDatabase:
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.ai_jobs: Dict[str, AIJob] = {}
        self.day_schedules: Dict[str, DaySchedule] = {}  # key: "YYYY-MM-DD"
    
    # ===== 任务操作 =====
    def create_task(self, task: Task) -> Task:
        """创建任务"""
        self.tasks[task.id] = task
        return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取单个任务"""
        return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> List[Task]:
        """获取所有任务"""
        return list(self.tasks.values())
    
    def update_task(self, task_id: str, task: Task) -> Optional[Task]:
        """更新任务"""
        if task_id in self.tasks:
            self.tasks[task_id] = task
            return task
        return None
    
    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        if task_id in self.tasks:
            del self.tasks[task_id]
            return True
        return False
    
    def get_tasks_by_tags(self, tags: List[str]) -> List[Task]:
        """根据标签筛选任务（AND逻辑）"""
        if not tags:
            return self.get_all_tasks()
        
        filtered_tasks = []
        for task in self.tasks.values():
            task_tags = task.task_tags or []
            if all(tag in task_tags for tag in tags):
                filtered_tasks.append(task)
        
        return filtered_tasks
    
    def get_tasks_for_date(self, target_date) -> List[Task]:
        """获取指定日期的任务"""
        tasks_for_date = []
        
        for task in self.tasks.values():
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
                tasks_for_date.append(task)
        
        return tasks_for_date
    
    # ===== AI作业操作 =====
    def create_ai_job(self, job: AIJob) -> AIJob:
        """创建AI作业"""
        self.ai_jobs[job.job_id] = job
        return job
    
    def get_ai_job(self, job_id: str) -> Optional[AIJob]:
        """获取AI作业"""
        return self.ai_jobs.get(job_id)
    
    def update_ai_job(self, job_id: str, job: AIJob) -> Optional[AIJob]:
        """更新AI作业"""
        if job_id in self.ai_jobs:
            self.ai_jobs[job_id] = job
            return job
        return None
    
    # ===== 日程安排操作 =====
    def create_day_schedule(self, date_str: str, schedule: DaySchedule) -> DaySchedule:
        """创建日程安排"""
        self.day_schedules[date_str] = schedule
        return schedule
    
    def get_day_schedule(self, date_str: str) -> Optional[DaySchedule]:
        """获取日程安排"""
        return self.day_schedules.get(date_str)
    
    def delete_day_schedule(self, date_str: str) -> bool:
        """删除日程安排"""
        if date_str in self.day_schedules:
            del self.day_schedules[date_str]
            return True
        return False
    
    # ===== 统计操作 =====
    def get_task_stats(self) -> dict:
        """获取任务统计信息"""
        from datetime import date
        from models import TaskTag, TaskStatus
        
        all_tasks = self.get_all_tasks()
        completed = sum(1 for t in all_tasks if t.completed)
        
        # 计算今日到期任务
        today = date.today()
        due_today = sum(1 for t in all_tasks 
                        if t.due_date and t.due_date.date() == today and not t.completed)
        
        # 计算逾期任务
        overdue = sum(1 for t in all_tasks 
                      if t.due_date and t.due_date.date() < today and not t.completed)

        # 统计各标签的任务数量
        tag_stats = {}
        for tag_enum in TaskTag:
            tag_value = tag_enum.value
            tag_stats[tag_value] = sum(1 for t in all_tasks 
                                      if t.task_tags and tag_value in t.task_tags)

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
            "by_tags": tag_stats
        }

# 全局数据库实例
db = InMemoryDatabase()
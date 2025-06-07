"""
数据库操作模块 - 简化标签系统后的版本
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

# 全局数据库实例
db = InMemoryDatabase()
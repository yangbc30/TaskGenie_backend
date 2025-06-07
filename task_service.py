"""
任务服务模块 - 简化标签系统后的版本
"""
import uuid
from typing import List, Optional
from datetime import datetime, date, timedelta

from models import Task, TaskCreate, TaskUpdate, TaskStatus
from database import db
from tag_service import TagService

class TaskService:
    @staticmethod
    def create_task(task_data: TaskCreate) -> Task:
        """创建新任务"""
        new_task = Task(
            id=str(uuid.uuid4()),
            name=task_data.name,
            description=task_data.description,
            created_at=datetime.now(),
            due_date=task_data.due_date,
            priority=task_data.priority,
            estimated_hours=task_data.estimated_hours,
            scheduled_date=task_data.scheduled_date,
        )
        
        return db.create_task(new_task)

    @staticmethod
    def get_task(task_id: str) -> Optional[Task]:
        """获取单个任务"""
        return db.get_task(task_id)

    @staticmethod
    def get_all_tasks() -> List[Task]:
        """获取所有任务"""
        return db.get_all_tasks()

    @staticmethod
    def get_tasks_by_tags(tags: List[str]) -> List[Task]:
        """根据标签筛选任务"""
        all_tasks = db.get_all_tasks()
        return TagService.get_tasks_by_tags(all_tasks, tags)

    @staticmethod
    def get_tasks_by_tag(tag: str) -> List[Task]:
        """根据单个标签获取任务"""
        all_tasks = db.get_all_tasks()
        return TagService.get_tasks_by_tag(all_tasks, tag)

    @staticmethod
    def update_task(task_id: str, task_update: TaskUpdate) -> Optional[Task]:
        """更新任务"""
        task = db.get_task(task_id)
        if not task:
            return None

        # 应用更新
        update_data = task_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(task, field, value)

        # 如果完成状态发生变化，更新相关状态
        if task.completed:
            task.status = TaskStatus.COMPLETED
        else:
            task.status = TaskStatus.PENDING

        return db.update_task(task_id, task)

    @staticmethod
    def delete_task(task_id: str) -> bool:
        """删除任务"""
        return db.delete_task(task_id)

    @staticmethod
    def get_calendar_tasks(year: int, month: int) -> dict:
        """获取指定月份的任务日历数据"""
        calendar_data = {}
        tasks = db.get_all_tasks()
        
        for task in tasks:
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

    @staticmethod
    def get_task_stats() -> dict:
        """获取任务统计信息"""
        tasks = db.get_all_tasks()
        completed = sum(1 for t in tasks if t.completed)
        
        # 计算今日到期任务
        today = date.today()
        due_today = sum(1 for t in tasks 
                        if t.due_date and t.due_date.date() == today and not t.completed)
        
        # 计算逾期任务
        overdue = sum(1 for t in tasks 
                      if t.due_date and t.due_date.date() < today and not t.completed)

        return {
            "total": len(tasks),
            "completed": completed,
            "pending": len(tasks) - completed,
            "due_today": due_today,
            "overdue": overdue,
            "by_priority": {
                "high": sum(1 for t in tasks if t.priority == "high" and not t.completed),
                "medium": sum(1 for t in tasks if t.priority == "medium" and not t.completed),
                "low": sum(1 for t in tasks if t.priority == "low" and not t.completed),
            },
            "by_status": {
                "pending": sum(1 for t in tasks if t.status == TaskStatus.PENDING),
                "in_progress": sum(1 for t in tasks if t.status == TaskStatus.IN_PROGRESS),
                "completed": sum(1 for t in tasks if t.status == TaskStatus.COMPLETED),
            },
            "by_tags": TagService.get_tag_stats(tasks)
        }
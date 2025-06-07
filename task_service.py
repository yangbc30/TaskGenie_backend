"""
任务服务模块
处理任务的CRUD操作和业务逻辑
"""
import uuid
from typing import List, Optional
from datetime import datetime, date, timedelta

from models import Task, TaskCreate, TaskUpdate, TaskStatus, TaskTag
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
            tags=task_data.tags,
            task_tags=task_data.task_tags or [],
            original_tags=[],
        )
        
        # 如果没有指定标签，自动分配标签
        if not new_task.task_tags:
            new_task.task_tags = TagService.auto_assign_task_tags(new_task)
        else:
            # 如果有指定标签，合并自动标签
            auto_tags = TagService.auto_assign_task_tags(new_task)
            new_task.task_tags = list(set(new_task.task_tags + auto_tags))
        
        return db.create_task(new_task)

    @staticmethod
    def get_task(task_id: str) -> Optional[Task]:
        """获取单个任务"""
        task = db.get_task(task_id)
        if task:
            TagService.update_task_tags(task)
        return task

    @staticmethod
    def get_all_tasks() -> List[Task]:
        """获取所有任务"""
        tasks = db.get_all_tasks()
        # 更新所有任务的标签
        for task in tasks:
            TagService.update_task_tags(task)
        return tasks

    @staticmethod
    def get_tasks_by_tags(tags: List[str]) -> List[Task]:
        """根据标签筛选任务"""
        tasks = db.get_tasks_by_tags(tags)
        # 更新所有任务的标签
        for task in tasks:
            TagService.update_task_tags(task)
        return tasks

    @staticmethod
    def update_task(task_id: str, task_update: TaskUpdate) -> Optional[Task]:
        """更新任务"""
        task = db.get_task(task_id)
        if not task:
            return None

        # 记录更新前的状态
        was_completed = task.completed
        
        # 应用更新
        update_data = task_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(task, field, value)

        # 如果完成状态发生变化，更新相关状态
        if task.completed != was_completed:
            if task.completed:
                task.status = TaskStatus.COMPLETED
            else:
                task.status = TaskStatus.PENDING

        # 更新任务标签
        TagService.update_task_tags(task)

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
                
            # 更新任务标签
            TagService.update_task_tags(task)
                
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
    def get_tasks_by_tag(tag: str) -> List[Task]:
        """根据单个标签获取任务（兼容旧接口）"""
        if tag not in [tag_enum.value for tag_enum in TaskTag]:
            return []
        
        tasks = db.get_all_tasks()
        # 更新所有任务的标签
        for task in tasks:
            TagService.update_task_tags(task)
        
        filtered_tasks = [task for task in tasks if task.task_tags and tag in task.task_tags]
        return filtered_tasks

    @staticmethod
    def get_task_stats() -> dict:
        """获取任务统计信息"""
        # 先更新所有任务的标签
        tasks = db.get_all_tasks()
        for task in tasks:
            TagService.update_task_tags(task)
        
        return db.get_task_stats()
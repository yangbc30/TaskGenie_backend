"""
标签服务模块
处理任务标签的自动分配和管理
"""
from typing import List
from datetime import datetime, timedelta
from models import Task, TaskTag

class TagService:
    @staticmethod
    def auto_assign_task_tags(task: Task) -> List[str]:
        """根据任务状态自动分配多个标签"""
        now = datetime.now()
        today = now.date()
        tomorrow = today + timedelta(days=1)
        
        assigned_tags = []
        
        # 如果任务已完成，只保留完成标签
        if task.completed:
            return [TaskTag.COMPLETED]
        
        # 时间相关标签
        if task.due_date:
            due_date = task.due_date.date()
            
            # 已过期
            if due_date < today:
                assigned_tags.append(TaskTag.OVERDUE)
                assigned_tags.append(TaskTag.URGENT)  # 过期任务自动标记为紧急
            # 今天到期
            elif due_date == today:
                assigned_tags.append(TaskTag.TODAY)
                if task.priority == "high":
                    assigned_tags.append(TaskTag.URGENT)
            # 明天到期
            elif due_date == tomorrow:
                assigned_tags.append(TaskTag.TOMORROW)
        else:
            # 没有截止日期的任务默认归类为今日
            assigned_tags.append(TaskTag.TODAY)
        
        # 优先级相关标签
        if task.priority == "high":
            assigned_tags.append(TaskTag.IMPORTANT)
            # 高优先级且时间紧迫的任务标记为紧急
            if task.due_date and task.due_date <= now + timedelta(days=1):
                assigned_tags.append(TaskTag.URGENT)
        
        # 基于任务名称和描述的智能标签分配
        task_content = f"{task.name} {task.description}".lower()
        
        # 工作相关关键词
        work_keywords = ["工作", "项目", "会议", "报告", "任务", "开发", "设计", "测试", "部署"]
        if any(keyword in task_content for keyword in work_keywords):
            assigned_tags.append(TaskTag.WORK)
        
        # 学习相关关键词
        learning_keywords = ["学习", "教程", "课程", "练习", "研究", "阅读", "掌握"]
        if any(keyword in task_content for keyword in learning_keywords):
            assigned_tags.append(TaskTag.LEARNING)
        
        # 项目相关关键词
        project_keywords = ["step", "阶段", "里程碑", "计划", "规划"]
        if any(keyword in task_content for keyword in project_keywords):
            assigned_tags.append(TaskTag.PROJECT)
        
        # 个人事务关键词
        personal_keywords = ["个人", "生活", "健康", "娱乐", "购物", "家庭"]
        if any(keyword in task_content for keyword in personal_keywords):
            assigned_tags.append(TaskTag.PERSONAL)
        
        # 如果没有分配到工作/学习/个人标签，默认为个人
        if not any(tag in assigned_tags for tag in [TaskTag.WORK, TaskTag.LEARNING, TaskTag.PERSONAL]):
            assigned_tags.append(TaskTag.PERSONAL)
        
        # 去重并返回
        return list(set(assigned_tags))

    @staticmethod
    def update_task_tags(task: Task):
        """更新任务的多标签，保留原始标签用于恢复"""
        # 如果任务刚刚完成
        if task.completed and TaskTag.COMPLETED not in (task.task_tags or []):
            # 保存当前标签作为原始标签
            if not task.original_tags:
                task.original_tags = task.task_tags or []
            # 设置为已完成
            task.task_tags = [TaskTag.COMPLETED]
        
        # 如果任务从完成状态变为未完成
        elif not task.completed and TaskTag.COMPLETED in (task.task_tags or []):
            # 如果有原始标签，恢复到原始标签
            if task.original_tags:
                task.task_tags = task.original_tags
                # 清除原始标签记录
                task.original_tags = []
            else:
                # 如果没有原始标签，重新自动分配
                task.task_tags = TagService.auto_assign_task_tags(task)
        
        # 如果任务没有完成，且不是从完成状态恢复，则自动更新标签
        elif not task.completed and TaskTag.COMPLETED not in (task.task_tags or []):
            # 自动分配标签
            auto_tags = TagService.auto_assign_task_tags(task)
            
            # 保留用户手动添加的标签（不在自动标签范围内的）
            manual_tags = []
            if task.task_tags:
                auto_tag_values = [tag.value if hasattr(tag, 'value') else tag for tag in auto_tags]
                manual_tags = [tag for tag in task.task_tags if tag not in auto_tag_values]
            
            # 合并自动标签和手动标签
            task.task_tags = list(set(auto_tags + manual_tags))

    @staticmethod
    def get_available_tags() -> dict:
        """获取所有可用的标签"""
        return {
            "system_tags": [tag.value for tag in TaskTag],
            "tag_descriptions": {
                TaskTag.TODAY: "今天需要完成的任务",
                TaskTag.TOMORROW: "明天需要完成的任务", 
                TaskTag.IMPORTANT: "重要的任务",
                TaskTag.URGENT: "紧急的任务",
                TaskTag.COMPLETED: "已完成的任务",
                TaskTag.OVERDUE: "已过期的任务",
                TaskTag.WORK: "工作相关的任务",
                TaskTag.PERSONAL: "个人事务",
                TaskTag.LEARNING: "学习相关的任务",
                TaskTag.PROJECT: "项目任务"
            }
        }
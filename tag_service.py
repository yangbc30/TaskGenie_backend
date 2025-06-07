"""
标签服务模块 - 基于任务属性动态计算标签
"""
from typing import List, Dict
from datetime import datetime, timedelta

class TagService:
    # 定义所有可能的标签
    AVAILABLE_TAGS = ["今日", "明日", "重要", "已完成", "已过期"]
    
    @staticmethod
    def get_task_tags(task) -> List[str]:
        """根据任务属性动态计算标签"""
        tags = []
        now = datetime.now()
        today = now.date()
        tomorrow = today + timedelta(days=1)
        
        # 已完成标签 - 最高优先级
        if task.completed:
            tags.append("已完成")
            return tags  # 已完成的任务只显示这一个标签
        
        # 时间相关标签
        if task.due_date:
            due_date = task.due_date.date()
            
            # 已过期 - 优先级高于今日/明日
            if due_date < today:
                tags.append("已过期")
            # 今日到期
            elif due_date == today:
                tags.append("今日")
            # 明日到期
            elif due_date == tomorrow:
                tags.append("明日")
        else:
            # 没有截止日期的任务默认归类为今日
            tags.append("今日")
        
        # 优先级标签
        if task.priority == "high":
            tags.append("重要")
        
        return tags
    
    @staticmethod
    def get_tasks_by_tag(tasks: List, tag: str) -> List:
        """根据标签筛选任务"""
        if tag not in TagService.AVAILABLE_TAGS:
            return []
        
        filtered_tasks = []
        for task in tasks:
            task_tags = TagService.get_task_tags(task)
            if tag in task_tags:
                filtered_tasks.append(task)
        
        return filtered_tasks
    
    @staticmethod
    def get_tasks_by_tags(tasks: List, tags: List[str]) -> List:
        """根据多个标签筛选任务（AND逻辑）"""
        if not tags:
            return tasks
        
        # 验证标签是否有效
        valid_tags = [tag for tag in tags if tag in TagService.AVAILABLE_TAGS]
        if not valid_tags:
            return tasks
        
        filtered_tasks = []
        for task in tasks:
            task_tags = TagService.get_task_tags(task)
            # 检查是否包含所有指定标签
            if all(tag in task_tags for tag in valid_tags):
                filtered_tasks.append(task)
        
        return filtered_tasks
    
    @staticmethod
    def get_available_tags() -> dict:
        """获取所有可用的标签"""
        return {
            "system_tags": TagService.AVAILABLE_TAGS,
            "tag_descriptions": {
                "今日": "今天需要完成的任务",
                "明日": "明天需要完成的任务",
                "重要": "高优先级的任务",
                "已完成": "已完成的任务",
                "已过期": "已过期的任务"
            }
        }
    
    @staticmethod
    def get_tag_stats(tasks: List) -> Dict[str, int]:
        """获取各标签的任务统计"""
        tag_stats = {}
        
        for tag in TagService.AVAILABLE_TAGS:
            tag_stats[tag] = len(TagService.get_tasks_by_tag(tasks, tag))
        
        return tag_stats
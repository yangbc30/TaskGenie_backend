"""
TaskGenie API 测试文件
测试所有后端API端点的功能
"""
import pytest
import asyncio
import json
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from typing import Dict, Any

# 导入主应用
from main import app
from database import db
from models import Task, TaskTag

# 创建测试客户端
client = TestClient(app)

class TestTaskGenieAPI:
    """TaskGenie API测试类"""
    
    def setup_method(self):
        """每个测试方法执行前的设置"""
        # 清空数据库
        db.tasks.clear()
        db.ai_jobs.clear()
        db.day_schedules.clear()
        print("\n🧹 清空测试数据")

    def teardown_method(self):
        """每个测试方法执行后的清理"""
        print("✅ 测试完成")

    # ===== 基础功能测试 =====
    def test_root_endpoint(self):
        """测试根路径端点"""
        print("\n🧪 测试根路径...")
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "TaskGenie API v2.0"
        assert "features" in data
        print("✅ 根路径测试通过")

    def test_health_check(self):
        """测试健康检查端点"""
        print("\n🧪 测试健康检查...")
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "2.0.0"
        print("✅ 健康检查测试通过")

    # ===== 任务管理测试 =====
    def test_create_task(self):
        """测试创建任务"""
        print("\n🧪 测试创建任务...")
        task_data = {
            "name": "测试任务",
            "description": "这是一个测试任务",
            "priority": "high",
            "estimated_hours": 2.5,
            "task_tags": ["重要", "工作"]
        }
        
        response = client.post("/tasks", json=task_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == task_data["name"]
        assert data["description"] == task_data["description"]
        assert data["priority"] == task_data["priority"]
        assert data["estimated_hours"] == task_data["estimated_hours"]
        assert "id" in data
        assert "created_at" in data
        assert isinstance(data["task_tags"], list)
        
        print(f"✅ 任务创建成功，ID: {data['id']}")
        return data

    def test_get_all_tasks(self):
        """测试获取所有任务"""
        print("\n🧪 测试获取所有任务...")
        
        # 先创建几个任务
        task1 = self.test_create_task()
        task2_data = {
            "name": "第二个任务",
            "description": "另一个测试任务",
            "priority": "medium"
        }
        task2_response = client.post("/tasks", json=task2_data)
        task2 = task2_response.json()
        
        # 获取所有任务
        response = client.get("/tasks")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        
        task_ids = [task["id"] for task in data]
        assert task1["id"] in task_ids
        assert task2["id"] in task_ids
        
        print(f"✅ 获取到 {len(data)} 个任务")
        return data

    def test_get_single_task(self):
        """测试获取单个任务"""
        print("\n🧪 测试获取单个任务...")
        
        # 先创建一个任务
        created_task = self.test_create_task()
        task_id = created_task["id"]
        
        # 获取任务
        response = client.get(f"/tasks/{task_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == task_id
        assert data["name"] == created_task["name"]
        
        print(f"✅ 成功获取任务: {data['name']}")

    def test_get_nonexistent_task(self):
        """测试获取不存在的任务"""
        print("\n🧪 测试获取不存在的任务...")
        
        response = client.get("/tasks/nonexistent-id")
        assert response.status_code == 404
        
        data = response.json()
        assert "任务不存在" in data["detail"]
        print("✅ 正确处理了不存在的任务")

    def test_update_task(self):
        """测试更新任务"""
        print("\n🧪 测试更新任务...")
        
        # 先创建一个任务
        created_task = self.test_create_task()
        task_id = created_task["id"]
        
        # 更新任务
        update_data = {
            "name": "更新后的任务名称",
            "completed": True,
            "priority": "low"
        }
        
        response = client.put(f"/tasks/{task_id}", json=update_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["completed"] == update_data["completed"]
        assert data["priority"] == update_data["priority"]
        assert TaskTag.COMPLETED in data["task_tags"]  # 完成任务应该有完成标签
        
        print(f"✅ 任务更新成功: {data['name']}")

    def test_delete_task(self):
        """测试删除任务"""
        print("\n🧪 测试删除任务...")
        
        # 先创建一个任务
        created_task = self.test_create_task()
        task_id = created_task["id"]
        
        # 删除任务
        response = client.delete(f"/tasks/{task_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert "任务已删除" in data["message"]
        
        # 验证任务已被删除
        get_response = client.get(f"/tasks/{task_id}")
        assert get_response.status_code == 404
        
        print("✅ 任务删除成功")

    # ===== 标签系统测试 =====
    def test_get_available_tags(self):
        """测试获取可用标签"""
        print("\n🧪 测试获取可用标签...")
        
        response = client.get("/tags")
        assert response.status_code == 200
        
        data = response.json()
        assert "system_tags" in data
        assert "tag_descriptions" in data
        assert isinstance(data["system_tags"], list)
        assert isinstance(data["tag_descriptions"], dict)
        
        # 检查基本标签是否存在
        expected_tags = ["今日", "明日", "重要", "紧急", "已完成", "已过期"]
        for tag in expected_tags:
            assert tag in data["system_tags"]
            assert tag in data["tag_descriptions"]
        
        print(f"✅ 获取到 {len(data['system_tags'])} 个可用标签")

    def test_filter_tasks_by_tags(self):
        """测试按标签筛选任务"""
        print("\n🧪 测试按标签筛选任务...")
        
        # 创建不同标签的任务
        task1_data = {
            "name": "重要工作任务",
            "priority": "high",
            "task_tags": ["重要", "工作"]
        }
        task2_data = {
            "name": "个人学习任务",
            "priority": "medium",
            "task_tags": ["学习", "个人"]
        }
        task3_data = {
            "name": "重要学习任务",
            "priority": "high",
            "task_tags": ["重要", "学习"]
        }
        
        client.post("/tasks", json=task1_data)
        client.post("/tasks", json=task2_data)
        client.post("/tasks", json=task3_data)
        
        # 按单个标签筛选
        response = client.get("/tasks/by-tags?tags=重要")
        assert response.status_code == 200
        data = response.json()
        # 应该返回2个重要任务
        important_tasks = [task for task in data if "重要" in task.get("task_tags", [])]
        assert len(important_tasks) >= 2
        
        # 按多个标签筛选（AND逻辑）
        response = client.get("/tasks/by-tags?tags=重要,学习")
        assert response.status_code == 200
        data = response.json()
        # 应该只返回同时包含"重要"和"学习"标签的任务
        filtered_tasks = [task for task in data 
                         if "重要" in task.get("task_tags", []) and "学习" in task.get("task_tags", [])]
        assert len(filtered_tasks) >= 1
        
        print("✅ 标签筛选功能正常")

    # ===== 日历功能测试 =====
    def test_get_calendar_tasks(self):
        """测试获取日历任务"""
        print("\n🧪 测试获取日历任务...")
        
        # 创建有截止日期的任务
        tomorrow = datetime.now() + timedelta(days=1)
        task_data = {
            "name": "明天的任务",
            "due_date": tomorrow.isoformat(),
            "priority": "medium"
        }
        
        client.post("/tasks", json=task_data)
        
        # 获取当前月份的日历数据
        year = tomorrow.year
        month = tomorrow.month
        
        response = client.get(f"/tasks/calendar/{year}/{month}")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        
        # 检查是否有明天的任务
        tomorrow_str = tomorrow.date().isoformat()
        if tomorrow_str in data:
            assert "due" in data[tomorrow_str]
            assert isinstance(data[tomorrow_str]["due"], list)
        
        print(f"✅ 获取到 {year}-{month} 的日历数据")

    # ===== 统计信息测试 =====
    def test_get_stats(self):
        """测试获取统计信息"""
        print("\n🧪 测试获取统计信息...")
        
        # 创建一些测试任务
        tasks_data = [
            {"name": "高优先级任务", "priority": "high"},
            {"name": "中优先级任务", "priority": "medium"},
            {"name": "已完成任务", "priority": "low", "completed": True},
        ]
        
        for task_data in tasks_data:
            client.post("/tasks", json=task_data)
        
        response = client.get("/stats")
        assert response.status_code == 200
        
        data = response.json()
        required_fields = ["total", "completed", "pending", "by_priority", "by_status", "by_tags"]
        for field in required_fields:
            assert field in data
        
        assert data["total"] == 3
        assert data["completed"] >= 1
        assert data["pending"] >= 2
        assert isinstance(data["by_priority"], dict)
        assert isinstance(data["by_status"], dict)
        assert isinstance(data["by_tags"], dict)
        
        print(f"✅ 统计信息正常: 总任务{data['total']}个，已完成{data['completed']}个")

    # ===== AI功能测试 =====
    def test_ai_task_planning(self):
        """测试AI任务规划"""
        print("\n🧪 测试AI任务规划...")
        
        planning_data = {
            "prompt": "学习Python编程",
            "max_tasks": 3
        }
        
        response = client.post("/ai/plan-tasks/async", json=planning_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "processing"
        assert data["max_tasks"] == 3
        
        job_id = data["job_id"]
        print(f"✅ AI规划任务已启动，作业ID: {job_id}")
        
        # 检查作业状态
        status_response = client.get(f"/ai/jobs/{job_id}")
        assert status_response.status_code == 200
        
        status_data = status_response.json()
        assert status_data["job_id"] == job_id
        assert status_data["status"] in ["pending", "processing", "completed", "failed"]
        
        print(f"✅ 作业状态: {status_data['status']}")
        
        return job_id

    def test_ai_job_status(self):
        """测试AI作业状态查询"""
        print("\n🧪 测试AI作业状态查询...")
        
        # 先启动一个AI任务
        job_id = self.test_ai_task_planning()
        
        # 查询作业状态
        response = client.get(f"/ai/jobs/{job_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["job_id"] == job_id
        assert "status" in data
        assert "created_at" in data
        
        print(f"✅ 作业状态查询成功: {data['status']}")

    def test_ai_job_not_found(self):
        """测试查询不存在的AI作业"""
        print("\n🧪 测试查询不存在的AI作业...")
        
        response = client.get("/ai/jobs/nonexistent-job-id")
        assert response.status_code == 404
        
        data = response.json()
        assert "任务不存在" in data["detail"]
        print("✅ 正确处理了不存在的AI作业")

    def test_ai_test_endpoint(self):
        """测试AI规划测试端点"""
        print("\n🧪 测试AI规划测试端点...")
        
        response = client.post("/ai/plan-tasks/test?prompt=测试任务&max_tasks=2")
        assert response.status_code == 200
        
        data = response.json()
        assert "success" in data
        
        if data["success"]:
            assert "tasks_created" in data
            assert "tasks" in data
            print(f"✅ AI测试成功，创建了 {data['tasks_created']} 个任务")
        else:
            print(f"⚠️ AI测试失败: {data.get('error', '未知错误')}")

    def test_day_schedule_preview(self):
        """测试日程安排预览"""
        print("\n🧪 测试日程安排预览...")
        
        # 创建今天的任务
        today = datetime.now().date()
        task_data = {
            "name": "今天的任务",
            "due_date": datetime.combine(today, datetime.min.time()).isoformat(),
            "priority": "high",
            "estimated_hours": 2.0
        }
        
        client.post("/tasks", json=task_data)
        
        # 获取今天的预览
        date_str = today.isoformat()
        response = client.get(f"/ai/schedule-day/{date_str}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["date"] == date_str
        assert "task_count" in data
        assert "total_estimated_hours" in data
        assert "high_priority_count" in data
        assert "tasks" in data
        
        assert data["task_count"] >= 1
        assert data["high_priority_count"] >= 1
        assert isinstance(data["tasks"], list)
        
        print(f"✅ 日程预览: {data['task_count']}个任务，{data['total_estimated_hours']}小时")

    # ===== 错误处理测试 =====
    def test_invalid_task_creation(self):
        """测试无效任务创建"""
        print("\n🧪 测试无效任务创建...")
        
        # 缺少必需字段
        invalid_data = {
            "description": "缺少name字段"
        }
        
        response = client.post("/tasks", json=invalid_data)
        assert response.status_code == 422  # 验证错误
        
        print("✅ 正确处理了无效的任务创建请求")

    def test_invalid_date_format(self):
        """测试无效日期格式"""
        print("\n🧪 测试无效日期格式...")
        
        response = client.get("/ai/schedule-day/invalid-date")
        assert response.status_code == 400
        
        data = response.json()
        assert "日期格式错误" in data["detail"]
        print("✅ 正确处理了无效的日期格式")

    # ===== 综合测试 =====
    def test_complete_workflow(self):
        """测试完整工作流程"""
        print("\n🧪 测试完整工作流程...")
        
        # 1. 创建任务
        task_data = {
            "name": "完整流程测试任务",
            "description": "测试完整的工作流程",
            "priority": "high",
            "estimated_hours": 3.0
        }
        
        create_response = client.post("/tasks", json=task_data)
        assert create_response.status_code == 200
        task = create_response.json()
        task_id = task["id"]
        
        # 2. 获取任务
        get_response = client.get(f"/tasks/{task_id}")
        assert get_response.status_code == 200
        
        # 3. 更新任务
        update_data = {"completed": True}
        update_response = client.put(f"/tasks/{task_id}", json=update_data)
        assert update_response.status_code == 200
        updated_task = update_response.json()
        assert updated_task["completed"] == True
        
        # 4. 获取统计信息
        stats_response = client.get("/stats")
        assert stats_response.status_code == 200
        stats = stats_response.json()
        assert stats["completed"] >= 1
        
        # 5. 删除任务
        delete_response = client.delete(f"/tasks/{task_id}")
        assert delete_response.status_code == 200
        
        print("✅ 完整工作流程测试通过")

def run_all_tests():
    """运行所有测试"""
    print("🚀 开始运行 TaskGenie API 测试套件")
    print("=" * 50)
    
    test_instance = TestTaskGenieAPI()
    
    # 定义所有测试方法
    test_methods = [
        test_instance.test_root_endpoint,
        test_instance.test_health_check,
        test_instance.test_create_task,
        test_instance.test_get_all_tasks,
        test_instance.test_get_single_task,
        test_instance.test_get_nonexistent_task,
        test_instance.test_update_task,
        test_instance.test_delete_task,
        test_instance.test_get_available_tags,
        test_instance.test_filter_tasks_by_tags,
        test_instance.test_get_calendar_tasks,
        test_instance.test_get_stats,
        test_instance.test_ai_task_planning,
        test_instance.test_ai_job_status,
        test_instance.test_ai_job_not_found,
        test_instance.test_ai_test_endpoint,
        test_instance.test_day_schedule_preview,
        test_instance.test_invalid_task_creation,
        test_instance.test_invalid_date_format,
        test_instance.test_complete_workflow,
    ]
    
    passed = 0
    failed = 0
    
    for test_method in test_methods:
        try:
            test_instance.setup_method()
            test_method()
            test_instance.teardown_method()
            passed += 1
        except Exception as e:
            print(f"❌ 测试失败: {test_method.__name__}")
            print(f"   错误: {str(e)}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 测试结果: {passed + failed} 个测试")
    print(f"✅ 通过: {passed}")
    print(f"❌ 失败: {failed}")
    print(f"📈 成功率: {passed / (passed + failed) * 100:.1f}%")
    
    if failed == 0:
        print("🎉 所有测试都通过了！")
    else:
        print("⚠️ 有测试失败，请检查错误信息")

if __name__ == "__main__":
    run_all_tests()
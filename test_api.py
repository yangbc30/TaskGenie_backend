
"""
TaskGenie API 简化测试文件
测试核心功能的可用性
"""
import requests
import json
import time
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"

class TaskGenieTest:
    def __init__(self):
        self.created_task_ids = []
        
    def log(self, message, success=True):
        """统一的日志输出"""
        emoji = "✅" if success else "❌"
        print(f"{emoji} {message}")
    
    def cleanup(self):
        """清理测试数据"""
        for task_id in self.created_task_ids:
            try:
                requests.delete(f"{BASE_URL}/tasks/{task_id}")
            except:
                pass
        self.created_task_ids.clear()
    
    def test_health_check(self):
        """测试健康检查"""
        try:
            response = requests.get(f"{BASE_URL}/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            self.log("健康检查通过")
            return True
        except Exception as e:
            self.log(f"健康检查失败: {e}", False)
            return False
    
    def test_create_task(self):
        """测试创建任务"""
        try:
            task_data = {
                "name": "测试任务",
                "description": "这是一个测试任务",
                "priority": "high",
                "estimated_hours": 2.5,
                "due_date": (datetime.now() + timedelta(days=1)).isoformat()
            }
            
            response = requests.post(f"{BASE_URL}/tasks", json=task_data)
            assert response.status_code == 200
            
            data = response.json()
            assert data["name"] == task_data["name"]
            assert data["priority"] == task_data["priority"]
            assert "id" in data
            
            self.created_task_ids.append(data["id"])
            self.log(f"任务创建成功: {data['name']}")
            return data
        except Exception as e:
            self.log(f"任务创建失败: {e}", False)
            return None
    
    def test_get_tasks(self):
        """测试获取任务列表"""
        try:
            response = requests.get(f"{BASE_URL}/tasks")
            assert response.status_code == 200
            
            data = response.json()
            assert isinstance(data, list)
            
            self.log(f"获取任务列表成功: {len(data)} 个任务")
            return data
        except Exception as e:
            self.log(f"获取任务列表失败: {e}", False)
            return []
    
    def test_update_task(self, task_id):
        """测试更新任务"""
        try:
            update_data = {
                "completed": True,
                "name": "更新后的任务名称"
            }
            
            response = requests.put(f"{BASE_URL}/tasks/{task_id}", json=update_data)
            assert response.status_code == 200
            
            data = response.json()
            assert data["completed"] == True
            assert data["name"] == update_data["name"]
            
            self.log("任务更新成功")
            return True
        except Exception as e:
            self.log(f"任务更新失败: {e}", False)
            return False
    
    def test_tag_system(self):
        """测试标签系统"""
        try:
            # 获取可用标签
            response = requests.get(f"{BASE_URL}/tags")
            assert response.status_code == 200
            
            data = response.json()
            assert "system_tags" in data
            assert "今日" in data["system_tags"]
            assert "明日" in data["system_tags"]
            assert "重要" in data["system_tags"]
            
            self.log("标签系统测试通过")
            
            # 测试按标签筛选
            response = requests.get(f"{BASE_URL}/tasks/by-tag/今日")
            assert response.status_code == 200
            
            self.log("标签筛选功能正常")
            return True
        except Exception as e:
            self.log(f"标签系统测试失败: {e}", False)
            return False
    
    def test_statistics(self):
        """测试统计功能"""
        try:
            response = requests.get(f"{BASE_URL}/stats")
            assert response.status_code == 200
            
            data = response.json()
            required_fields = ["total", "completed", "pending", "by_priority", "by_tags"]
            for field in required_fields:
                assert field in data
            
            self.log(f"统计信息正常: 总任务{data['total']}个")
            return True
        except Exception as e:
            self.log(f"统计功能测试失败: {e}", False)
            return False
    
    def test_ai_planning(self):
        """测试AI任务规划"""
        try:
            planning_data = {
                "prompt": "学习Python编程基础",
                "max_tasks": 3
            }
            
            response = requests.post(f"{BASE_URL}/ai/plan-tasks/async", json=planning_data)
            assert response.status_code == 200
            
            data = response.json()
            assert "job_id" in data
            assert data["status"] == "processing"
            
            job_id = data["job_id"]
            self.log(f"AI规划任务启动成功: {job_id}")
            
            # 等待处理完成（简化测试，只等待几秒）
            time.sleep(3)
            
            # 检查作业状态
            response = requests.get(f"{BASE_URL}/ai/jobs/{job_id}")
            assert response.status_code == 200
            
            job_data = response.json()
            self.log(f"AI作业状态: {job_data['status']}")
            
            return True
        except Exception as e:
            self.log(f"AI规划测试失败: {e}", False)
            return False
    
    def test_calendar_view(self):
        """测试日历视图"""
        try:
            now = datetime.now()
            year = now.year
            month = now.month
            
            response = requests.get(f"{BASE_URL}/tasks/calendar/{year}/{month}")
            assert response.status_code == 200
            
            data = response.json()
            assert isinstance(data, dict)
            
            self.log(f"日历视图正常: {year}-{month}")
            return True
        except Exception as e:
            self.log(f"日历视图测试失败: {e}", False)
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始 TaskGenie API 测试")
        print("=" * 40)
        
        tests = [
            ("健康检查", self.test_health_check),
            ("任务创建", self.test_create_task),
            ("任务列表", self.test_get_tasks),
            ("标签系统", self.test_tag_system),
            ("统计功能", self.test_statistics),
            ("AI规划", self.test_ai_planning),
            ("日历视图", self.test_calendar_view),
        ]
        
        passed = 0
        failed = 0
        
        created_task = None
        
        for test_name, test_func in tests:
            print(f"\n🧪 测试 {test_name}...")
            try:
                if test_name == "任务创建":
                    result = test_func()
                    created_task = result
                    if result:
                        passed += 1
                    else:
                        failed += 1
                elif test_name == "任务更新" and created_task:
                    result = test_func(created_task["id"])
                    if result:
                        passed += 1
                    else:
                        failed += 1
                else:
                    result = test_func()
                    if result:
                        passed += 1
                    else:
                        failed += 1
                        
            except Exception as e:
                self.log(f"{test_name} 执行异常: {e}", False)
                failed += 1
        
        # 如果有创建的任务，测试更新功能
        if created_task:
            print(f"\n🧪 测试任务更新...")
            if self.test_update_task(created_task["id"]):
                passed += 1
            else:
                failed += 1
        
        # 清理测试数据
        self.cleanup()
        
        print("\n" + "=" * 40)
        print(f"📊 测试结果: {passed + failed} 个测试")
        print(f"✅ 通过: {passed}")
        print(f"❌ 失败: {failed}")
        print(f"📈 成功率: {passed / (passed + failed) * 100:.1f}%")
        
        if failed == 0:
            print("🎉 所有测试都通过了！")
        else:
            print("⚠️ 有测试失败，请检查错误信息")
        
        return failed == 0

def quick_test():
    """快速测试核心功能"""
    print("🔥 快速测试模式")
    
    try:
        # 测试服务器是否运行
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ 服务器运行正常")
        else:
            print("❌ 服务器响应异常")
            return False
            
        # 测试基本API
        response = requests.get(f"{BASE_URL}/tasks")
        if response.status_code == 200:
            tasks = response.json()
            print(f"✅ API正常，当前有 {len(tasks)} 个任务")
        else:
            print("❌ API响应异常")
            return False
            
        print("🎉 快速测试通过！")
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器，请确保后端服务已启动")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "quick":
        quick_test()
    else:
        tester = TaskGenieTest()
        tester.run_all_tests()
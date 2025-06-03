# test_ai_date_planning.py
import requests
import json
import time
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"

def test_ai_date_planning():
    print("=== 测试 AI 日期规划功能 ===\n")
    
    # 测试用例1：明天的生日派对
    print("测试用例1：准备明天的生日派对")
    ai_request = {
        "prompt": "准备明天晚上7点的生日派对，大约20人参加",
        "max_tasks": 3
    }
    
    response = requests.post(f"{BASE_URL}/ai/plan-tasks/async", json=ai_request)
    if response.status_code == 200:
        job_id = response.json()["job_id"]
        print(f"任务已提交，Job ID: {job_id}")
        
        # 等待AI处理
        print("等待AI处理...")
        time.sleep(5)
        
        # 检查结果
        response = requests.get(f"{BASE_URL}/ai/jobs/{job_id}")
        if response.status_code == 200:
            job = response.json()
            if job["status"] == "completed":
                tasks = job["result"]
                print(f"\nAI生成了 {len(tasks)} 个任务：")
                for task in tasks:
                    print(f"\n任务：{task['name']}")
                    print(f"  描述：{task['description']}")
                    print(f"  优先级：{task['priority']}")
                    print(f"  预计时长：{task.get('estimated_hours', 'N/A')} 小时")
                    if task.get('due_date'):
                        due_date = datetime.fromisoformat(task['due_date'].replace('Z', '+00:00'))
                        print(f"  截止时间：{due_date.strftime('%Y-%m-%d %H:%M')}")
                    else:
                        print(f"  截止时间：未设置")
            else:
                print(f"任务状态：{job['status']}")
                if job.get('error'):
                    print(f"错误：{job['error']}")
    
    print("\n" + "-"*50 + "\n")
    
    # 测试用例2：本周的项目
    print("测试用例2：本周五之前完成项目报告")
    ai_request = {
        "prompt": "本周五之前需要完成季度项目报告，包括数据分析和PPT制作",
        "max_tasks": 3
    }
    
    response = requests.post(f"{BASE_URL}/ai/plan-tasks/async", json=ai_request)
    if response.status_code == 200:
        job_id = response.json()["job_id"]
        print(f"任务已提交，Job ID: {job_id}")
        
        # 等待AI处理
        print("等待AI处理...")
        time.sleep(5)
        
        # 检查结果
        response = requests.get(f"{BASE_URL}/ai/jobs/{job_id}")
        if response.status_code == 200:
            job = response.json()
            if job["status"] == "completed":
                tasks = job["result"]
                print(f"\nAI生成了 {len(tasks)} 个任务：")
                for task in tasks:
                    print(f"\n任务：{task['name']}")
                    print(f"  优先级：{task['priority']}")
                    if task.get('due_date'):
                        due_date = datetime.fromisoformat(task['due_date'].replace('Z', '+00:00'))
                        print(f"  截止时间：{due_date.strftime('%Y-%m-%d %H:%M')}")
                        
                        # 检查是否在本周五之前
                        now = datetime.now()
                        days_until_friday = (4 - now.weekday()) % 7
                        if days_until_friday == 0:
                            days_until_friday = 7
                        friday = now.replace(hour=18, minute=0, second=0) + timedelta(days=days_until_friday)
                        
                        if due_date <= friday:
                            print(f"  ✓ 在本周五之前")
                        else:
                            print(f"  ✗ 超过本周五")

if __name__ == "__main__":
    test_ai_date_planning()
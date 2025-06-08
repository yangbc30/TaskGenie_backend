# TaskGenie Backend

> 基于 FastAPI 的智能任务管理系统后端服务

## 🚀 快速开始

### 环境要求
- Python 3.9+
- pip 或 poetry

### 安装与运行
```bash
# 克隆项目
git clone https://github.com/your-username/taskgenie-backend.git
cd taskgenie-backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt

# 启动服务
python run.py
# 或
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

服务运行在: http://localhost:8000

## 📚 API 文档

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## ✨ 主要功能

- 🤖 **AI任务规划** - 智能分解复杂目标为具体可执行任务
- 📅 **AI日程安排** - 基于优先级和时间的智能排程
- 🏷️ **动态标签计算** - 实时计算任务标签（今日、明日、重要等）
- 📊 **任务统计分析** - 提供详细的任务数据统计
- 🔄 **异步处理** - 后台处理AI请求，不阻塞用户操作

## 🏗️ 技术架构

- **框架**: FastAPI 0.104+
- **AI服务**: OpenAI GPT (硅谷云端)
- **数据验证**: Pydantic 2.0+
- **异步处理**: BackgroundTasks
- **服务器**: Uvicorn ASGI

## 📁 项目结构

```
├── main.py              # 应用入口
├── config.py            # 配置管理
├── models.py            # 数据模型
├── database.py          # 数据访问层
├── api_routes.py        # API路由
├── task_service.py      # 任务服务
├── ai_service.py        # AI服务
├── tag_service.py       # 标签服务
├── run.py               # 启动脚本
└── requirements.txt     # 依赖列表
```

## ⚙️ 环境配置

创建 `.env` 文件（可选）：

```env
# AI 配置
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://api.siliconflow.cn/v1

# 服务配置
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=True

# 其他配置
MAX_TASKS_PER_PLANNING=10
```

## 🔧 核心 API

### 任务管理
```
POST   /tasks              # 创建任务
GET    /tasks              # 获取任务列表
PUT    /tasks/{id}         # 更新任务
DELETE /tasks/{id}         # 删除任务
GET    /tasks/by-tags      # 按标签筛选
```

### AI 功能
```
POST   /ai/plan-tasks/async      # 异步AI任务规划
GET    /ai/jobs/{job_id}         # 查询AI作业状态
POST   /ai/schedule-day/async    # 异步AI日程安排
GET    /ai/schedule/{date}       # 获取日程安排
```

### 其他接口
```
GET    /stats              # 任务统计
GET    /tags               # 可用标签
GET    /health             # 健康检查
```

## 🧪 开发调试

### 运行测试
```bash
# 简单测试
python test_api.py

# 快速验证
python test_api.py quick

# 完整测试
python backend_test.py
```

### 查看日志
```bash
# 启动时查看详细日志
python run.py
# 日志级别: INFO, DEBUG, WARNING
```

### API 测试示例
```bash
# 创建任务
curl -X POST "http://localhost:8000/tasks" \
  -H "Content-Type: application/json" \
  -d '{"name": "测试任务", "priority": "high"}'

# AI 任务规划
curl -X POST "http://localhost:8000/ai/plan-tasks/async" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "学习Python", "max_tasks": 3}'
```

## 🐛 常见问题

**依赖安装失败**
```bash
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

**AI API 调用失败**
- 检查 API Key 是否正确
- 确认网络连接正常
- 查看控制台错误日志

**端口占用**
```bash
# 查找占用端口的进程
lsof -i :8000
# 终止进程
kill -9 <PID>
```

## 🚀 部署

### Docker 部署
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "run.py"]
```

### 生产环境
```bash
export ENVIRONMENT=production
export OPENAI_API_KEY=your-production-key
python run.py
```

## 📊 性能监控

- **响应时间**: 目标 API 响应 <500ms
- **AI处理**: 任务规划 <30s，日程安排 <15s
- **并发支持**: 支持多用户同时使用
- **错误率**: 目标 <1%

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支: `git checkout -b feature/new-feature`
3. 提交更改: `git commit -m 'Add new feature'`
4. 推送分支: `git push origin feature/new-feature`
5. 提交 Pull Request

## 📄 许可证

MIT License
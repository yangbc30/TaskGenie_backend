# TaskGenie Backend v2.0

智能任务管理系统后端 - 模块化重构版本

## 🏗️ 项目结构

```
backend/
├── main.py              # 主应用文件
├── run.py               # 运行脚本
├── config.py            # 配置文件
├── models.py            # 数据模型
├── database.py          # 数据库操作
├── task_service.py      # 任务服务
├── ai_service.py        # AI服务
├── tag_service.py       # 标签服务
├── api_routes.py        # API路由
└── requirements.txt     # 依赖列表
```

## 🚀 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 设置环境变量（可选）
```bash
export OPENAI_API_KEY="your-api-key"
export OPENAI_BASE_URL="your-base-url"
export DEBUG="True"
```

### 3. 启动服务
```bash
# 方式1：使用运行脚本
python run.py

# 方式2：直接运行主文件
python main.py

# 方式3：使用uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. 访问API文档
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 📁 模块说明

### models.py
- 定义所有的数据模型
- 包含任务、AI作业、日程安排等模型
- 使用Pydantic进行数据验证

### database.py
- 数据库操作抽象层
- 目前使用内存存储，后续可轻松替换为真实数据库
- 提供CRUD操作接口

### task_service.py
- 任务相关的业务逻辑
- 处理任务的创建、更新、删除等操作
- 集成标签自动分配功能

### ai_service.py
- AI功能相关服务
- 处理任务规划和日程安排
- 与OpenAI API交互

### tag_service.py
- 标签管理服务
- 自动标签分配算法
- 多标签系统支持

### api_routes.py
- 定义所有API端点
- 按功能分组路由
- 包含请求验证和错误处理

### config.py
- 集中配置管理
- 支持环境变量配置
- 区分开发和生产环境

## 🎯 主要功能

### 任务管理
- ✅ 创建、读取、更新、删除任务
- ✅ 多标签系统支持
- ✅ 任务状态管理
- ✅ 日历视图支持

### AI功能
- ✅ 智能任务规划
- ✅ 自动任务分解
- ✅ 智能日程安排
- ✅ 异步处理支持

### 标签系统
- ✅ 自动标签分配
- ✅ 多标签筛选
- ✅ 智能分类算法
- ✅ 标签管理接口

## 🔧 API端点

### 任务相关
- `POST /tasks` - 创建任务
- `GET /tasks` - 获取所有任务
- `GET /tasks/{id}` - 获取单个任务
- `PUT /tasks/{id}` - 更新任务
- `DELETE /tasks/{id}` - 删除任务
- `GET /tasks/by-tags` - 按标签筛选任务
- `GET /tasks/calendar/{year}/{month}` - 获取日历数据

### AI功能
- `POST /ai/plan-tasks/async` - 异步任务规划
- `GET /ai/jobs/{job_id}` - 获取AI作业状态
- `POST /ai/schedule-day/async` - 异步日程安排
- `GET /ai/schedule/{date}` - 获取日程安排
- `DELETE /ai/schedule/{date}` - 删除日程安排

### 通用接口
- `GET /stats` - 获取统计信息
- `GET /tags` - 获取可用标签
- `GET /health` - 健康检查

## 🔄 模块化优势

### 1. 清晰的代码组织
- 按功能模块分离代码
- 降低代码耦合度
- 提高代码可读性

### 2. 易于维护和扩展
- 模块独立开发
- 便于单元测试
- 支持功能迭代

### 3. 更好的错误隔离
- 模块级错误处理
- 不影响其他功能
- 便于问题定位

### 4. 团队协作友好
- 模块间职责明确
- 支持并行开发
- 减少代码冲突

## 🚀 部署说明

### 开发环境
```bash
python run.py
```

### 生产环境
```bash
export ENVIRONMENT=production
export OPENAI_API_KEY="your-production-key"
python run.py
```

### Docker部署（可选）
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "run.py"]
```

## 📝 更新日志

### v2.0.0
- ✅ 完全模块化重构
- ✅ 多标签系统支持
- ✅ 改进的AI服务
- ✅ 更好的错误处理
- ✅ 配置管理优化
- ✅ API文档完善

### v1.0.0
- ✅ 基础任务管理
- ✅ AI任务规划
- ✅ 日程安排功能

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 📄 许可证

MIT License
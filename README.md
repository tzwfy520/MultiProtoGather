# MultiProtGather - 多协议数据采集系统

## 项目简介

MultiProtGather 是一个基于 Django + React 的多协议数据采集系统，支持通过 SSH、Telnet、SNMP 等协议从网络设备采集数据，并提供数据分析和可视化功能。

## 功能特性

- 🌐 **多协议支持**: SSH、Telnet、SNMP 协议数据采集
- 📊 **数据分析**: 采集数据的统计分析和可视化
- 🎯 **任务管理**: 灵活的采集任务调度和管理
- 📱 **现代化UI**: 基于 Ant Design 的响应式前端界面
- 🔄 **异步处理**: Celery 异步任务队列支持
- 🐳 **容器化部署**: Docker 和 Docker Compose 一键部署
- 📈 **实时监控**: 任务执行状态实时监控

## 技术栈

### 后端
- **框架**: Django 4.x + Django REST Framework
- **数据库**: PostgreSQL
- **缓存**: Redis
- **任务队列**: Celery + Redis
- **API文档**: drf-spectacular (OpenAPI 3.0)

### 前端
- **框架**: React 18 + TypeScript
- **UI组件**: Ant Design
- **状态管理**: React Hooks
- **HTTP客户端**: Axios
- **构建工具**: Create React App

### 部署
- **容器化**: Docker + Docker Compose
- **Web服务器**: Nginx
- **进程管理**: Supervisor

## 快速开始

### 使用 Docker Compose（推荐）

1. **克隆项目**
```bash
git clone <repository-url>
cd MultiProtGather
```

2. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件，修改数据库密码等敏感信息
```

3. **启动服务**
```bash
# 构建并启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

4. **初始化数据库**
```bash
# 执行数据库迁移
docker-compose exec backend python manage.py migrate

# 创建超级用户
docker-compose exec backend python manage.py createsuperuser

# 收集静态文件
docker-compose exec backend python manage.py collectstatic --noinput
```

5. **访问应用**
- 前端应用: http://localhost
- 后端API: http://localhost:8000
- API文档: http://localhost:8000/api/docs/
- 管理后台: http://localhost:8000/admin/
- Celery监控: http://localhost:5555

### 本地开发环境

#### 后端开发

1. **环境准备**
```bash
cd multiprotgather-backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **数据库配置**
```bash
# 安装 PostgreSQL 和 Redis
# 创建数据库
createdb multiprotgather

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件
```

3. **启动服务**
```bash
# 数据库迁移
python manage.py migrate

# 创建超级用户
python manage.py createsuperuser

# 启动开发服务器
python manage.py runserver

# 启动 Celery Worker（新终端）
celery -A multiprotgather worker -l info

# 启动 Celery Beat（新终端）
celery -A multiprotgather beat -l info
```

#### 前端开发

1. **环境准备**
```bash
cd multiprotgather-frontend
npm install
```

2. **启动开发服务器**
```bash
npm start
```

3. **构建生产版本**
```bash
npm run build
```

## 项目结构

```
MultiProtGather/
├── multiprotgather-backend/     # Django 后端
│   ├── apps/                    # 应用模块
│   │   ├── devices/            # 设备管理
│   │   ├── tasks/              # 任务管理
│   │   ├── collectors/         # 数据采集器
│   │   └── results/            # 结果分析
│   ├── multiprotgather/        # 项目配置
│   ├── requirements.txt        # Python依赖
│   └── Dockerfile             # 后端Docker配置
├── multiprotgather-frontend/    # React 前端
│   ├── src/
│   │   ├── components/         # 通用组件
│   │   ├── pages/             # 页面组件
│   │   ├── services/          # API服务
│   │   └── types/             # TypeScript类型
│   ├── package.json           # Node.js依赖
│   └── Dockerfile            # 前端Docker配置
├── docker-compose.yml         # Docker编排配置
├── init.sql                  # 数据库初始化脚本
└── README.md                 # 项目文档
```

## API 文档

启动后端服务后，可以通过以下地址访问 API 文档：

- **Swagger UI**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/redoc/
- **OpenAPI Schema**: http://localhost:8000/api/schema/

## 主要功能模块

### 1. 设备管理
- 设备信息的增删改查
- 支持 SSH、Telnet、SNMP 连接配置
- 设备连接状态检测

### 2. 任务管理
- 采集任务的创建和调度
- 任务模板管理
- 任务执行历史查看

### 3. 数据采集
- 多协议数据采集支持
- 异步任务执行
- 采集结果存储

### 4. 数据分析
- 采集数据统计分析
- 数据可视化展示
- 结果导出功能

## 配置说明

### 环境变量

主要环境变量说明：

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `DEBUG` | 调试模式 | `False` |
| `SECRET_KEY` | Django密钥 | 需要设置 |
| `DATABASE_URL` | 数据库连接 | PostgreSQL |
| `REDIS_URL` | Redis连接 | `redis://redis:6379/0` |
| `ALLOWED_HOSTS` | 允许的主机 | `localhost,127.0.0.1` |

### 数据库配置

默认使用 PostgreSQL 数据库，配置信息：

```
Host: localhost (Docker: db)
Port: 5432
Database: multiprotgather
Username: postgres
Password: postgres123
```

## 部署指南

### 生产环境部署

1. **服务器准备**
   - 安装 Docker 和 Docker Compose
   - 确保防火墙开放必要端口（80, 443, 8000）

2. **配置修改**
   ```bash
   # 复制并修改环境配置
   cp .env.example .env
   
   # 修改以下配置：
   # - SECRET_KEY: 生成新的密钥
   # - POSTGRES_PASSWORD: 修改数据库密码
   # - ALLOWED_HOSTS: 添加域名
   # - CORS_ALLOWED_ORIGINS: 添加前端域名
   ```

3. **SSL证书配置**（可选）
   - 修改 nginx.conf 添加 SSL 配置
   - 使用 Let's Encrypt 或其他证书

4. **启动服务**
   ```bash
   docker-compose -f docker-compose.yml up -d
   ```

### 监控和维护

- **日志查看**: `docker-compose logs -f [service_name]`
- **服务重启**: `docker-compose restart [service_name]`
- **数据备份**: 定期备份 PostgreSQL 数据
- **更新部署**: `docker-compose pull && docker-compose up -d`

## 开发指南

### 后端开发

1. **添加新的API端点**
   - 在对应的 `views.py` 中添加视图
   - 在 `urls.py` 中配置路由
   - 在 `serializers.py` 中定义序列化器

2. **数据库模型修改**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

3. **添加异步任务**
   - 在 `tasks.py` 中定义任务
   - 使用 `@shared_task` 装饰器

### 前端开发

1. **添加新页面**
   - 在 `src/pages/` 下创建组件
   - 在路由配置中添加路径

2. **API集成**
   - 在 `src/services/api.ts` 中添加API方法
   - 使用 TypeScript 类型定义

3. **组件开发**
   - 使用 Ant Design 组件
   - 遵循 React Hooks 最佳实践

## 故障排除

### 常见问题

1. **容器启动失败**
   - 检查端口占用: `netstat -tlnp | grep :80`
   - 查看容器日志: `docker-compose logs [service_name]`

2. **数据库连接失败**
   - 确认数据库服务状态
   - 检查环境变量配置

3. **前端无法访问后端API**
   - 检查 CORS 配置
   - 确认网络连通性

4. **Celery任务不执行**
   - 检查 Redis 连接
   - 查看 Worker 日志

### 性能优化

1. **数据库优化**
   - 添加适当的索引
   - 优化查询语句

2. **缓存策略**
   - 使用 Redis 缓存频繁查询
   - 实现查询结果缓存

3. **前端优化**
   - 代码分割和懒加载
   - 图片和资源优化

## 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 联系方式

- 项目维护者: [Your Name]
- 邮箱: [your.email@example.com]
- 项目地址: [GitHub Repository URL]

## 更新日志

### v1.0.0 (2024-01-XX)
- 初始版本发布
- 基础的多协议数据采集功能
- Web管理界面
- Docker容器化部署支持
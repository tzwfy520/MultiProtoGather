# MultiProtGather API 使用指南

本文档详细介绍了 MultiProtGather 系统的 REST API 接口使用方法。

## API 概述

### 基础信息

- **Base URL**: `http://localhost:8000/api/v1/`
- **认证方式**: Token Authentication
- **数据格式**: JSON
- **字符编码**: UTF-8

### 认证

所有 API 请求都需要在 Header 中包含认证 Token：

```http
Authorization: Token your-auth-token-here
```

获取 Token：

```bash
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_username",
    "password": "your_password"
  }'
```

响应：
```json
{
  "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b",
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com"
  }
}
```

### 响应格式

成功响应：
```json
{
  "success": true,
  "data": {...},
  "message": "操作成功"
}
```

错误响应：
```json
{
  "success": false,
  "error": "错误信息",
  "details": {...}
}
```

分页响应：
```json
{
  "success": true,
  "data": {
    "count": 100,
    "next": "http://localhost:8000/api/v1/devices/?page=3",
    "previous": "http://localhost:8000/api/v1/devices/?page=1",
    "results": [...]
  }
}
```

## 设备管理 API

### 1. 获取设备列表

```http
GET /api/v1/devices/
```

**查询参数**:
- `page`: 页码 (默认: 1)
- `page_size`: 每页数量 (默认: 20, 最大: 100)
- `search`: 搜索关键词 (搜索名称、IP地址)
- `protocol`: 协议过滤 (ssh, telnet, snmp)
- `status`: 状态过滤 (active, inactive)

**示例请求**:
```bash
curl -X GET "http://localhost:8000/api/v1/devices/?protocol=ssh&status=active" \
  -H "Authorization: Token your-token"
```

**响应**:
```json
{
  "success": true,
  "data": {
    "count": 2,
    "results": [
      {
        "id": 1,
        "name": "Router-01",
        "ip_address": "192.168.1.1",
        "protocol": "ssh",
        "port": 22,
        "username": "admin",
        "status": "active",
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-15T10:30:00Z"
      }
    ]
  }
}
```

### 2. 创建设备

```http
POST /api/v1/devices/
```

**请求体**:
```json
{
  "name": "Switch-01",
  "ip_address": "192.168.1.10",
  "protocol": "ssh",
  "port": 22,
  "username": "admin",
  "password": "password123",
  "description": "核心交换机"
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "id": 2,
    "name": "Switch-01",
    "ip_address": "192.168.1.10",
    "protocol": "ssh",
    "port": 22,
    "username": "admin",
    "status": "active",
    "created_at": "2024-01-15T11:00:00Z"
  },
  "message": "设备创建成功"
}
```

### 3. 获取设备详情

```http
GET /api/v1/devices/{id}/
```

### 4. 更新设备

```http
PUT /api/v1/devices/{id}/
PATCH /api/v1/devices/{id}/
```

### 5. 删除设备

```http
DELETE /api/v1/devices/{id}/
```

### 6. 测试设备连接

```http
POST /api/v1/devices/{id}/test-connection/
```

**响应**:
```json
{
  "success": true,
  "data": {
    "connected": true,
    "response_time": 0.15,
    "message": "连接成功"
  }
}
```

## 任务管理 API

### 1. 获取任务列表

```http
GET /api/v1/tasks/
```

**查询参数**:
- `status`: 任务状态 (pending, running, completed, failed)
- `device_id`: 设备ID过滤
- `created_after`: 创建时间过滤 (ISO 8601格式)
- `created_before`: 创建时间过滤

### 2. 创建采集任务

```http
POST /api/v1/tasks/
```

**请求体**:
```json
{
  "name": "网络设备信息采集",
  "device_ids": [1, 2, 3],
  "commands": [
    "show version",
    "show interfaces",
    "show ip route"
  ],
  "schedule_type": "immediate",
  "description": "采集网络设备基础信息"
}
```

**定时任务**:
```json
{
  "name": "定时采集任务",
  "device_ids": [1],
  "commands": ["show interfaces"],
  "schedule_type": "cron",
  "cron_expression": "0 */6 * * *",
  "description": "每6小时采集一次接口状态"
}
```

### 3. 获取任务执行历史

```http
GET /api/v1/tasks/{id}/executions/
```

### 4. 手动执行任务

```http
POST /api/v1/tasks/{id}/execute/
```

### 5. 停止任务执行

```http
POST /api/v1/tasks/{id}/stop/
```

## 任务模板 API

### 1. 获取模板列表

```http
GET /api/v1/task-templates/
```

### 2. 创建任务模板

```http
POST /api/v1/task-templates/
```

**请求体**:
```json
{
  "name": "接口状态检查模板",
  "description": "检查设备接口状态的标准模板",
  "commands": [
    "show interfaces status",
    "show interfaces description"
  ],
  "collector": "ssh",
  "timeout": 30,
  "retry_count": 3
}
```

### 3. 从模板创建任务

```http
POST /api/v1/task-templates/{id}/create-task/
```

**请求体**:
```json
{
  "name": "基于模板的采集任务",
  "device_ids": [1, 2, 3],
  "schedule_type": "immediate"
}
```

## 采集结果 API

### 1. 获取采集结果

```http
GET /api/v1/results/
```

**查询参数**:
- `task_id`: 任务ID过滤
- `device_id`: 设备ID过滤
- `status`: 结果状态 (success, failed)
- `date_from`: 开始日期
- `date_to`: 结束日期

### 2. 获取结果详情

```http
GET /api/v1/results/{id}/
```

**响应**:
```json
{
  "success": true,
  "data": {
    "id": 1,
    "task_id": 1,
    "device_id": 1,
    "status": "success",
    "output": "Cisco IOS Software, Version 15.1...",
    "error_message": null,
    "execution_time": 2.5,
    "created_at": "2024-01-15T12:00:00Z"
  }
}
```

### 3. 导出结果

```http
GET /api/v1/results/export/
```

**查询参数**:
- `format`: 导出格式 (csv, json, xlsx)
- `task_id`: 任务ID过滤
- `date_from`: 开始日期
- `date_to`: 结束日期

## 数据分析 API

### 1. 获取统计数据

```http
GET /api/v1/analysis/stats/
```

**响应**:
```json
{
  "success": true,
  "data": {
    "total_devices": 10,
    "active_devices": 8,
    "total_tasks": 25,
    "completed_tasks": 20,
    "failed_tasks": 2,
    "success_rate": 90.9,
    "avg_execution_time": 3.2
  }
}
```

### 2. 获取趋势数据

```http
GET /api/v1/analysis/trends/
```

**查询参数**:
- `period`: 时间周期 (day, week, month)
- `metric`: 指标类型 (task_count, success_rate, execution_time)

### 3. 创建分析报告

```http
POST /api/v1/analysis/reports/
```

**请求体**:
```json
{
  "name": "月度采集报告",
  "description": "2024年1月采集情况分析",
  "date_from": "2024-01-01",
  "date_to": "2024-01-31",
  "include_charts": true,
  "device_ids": [1, 2, 3]
}
```

## 系统管理 API

### 1. 系统健康检查

```http
GET /api/v1/health/
```

**响应**:
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "database": "connected",
    "redis": "connected",
    "celery": "running",
    "version": "1.0.0",
    "uptime": "5 days, 3 hours"
  }
}
```

### 2. 获取系统信息

```http
GET /api/v1/system/info/
```

### 3. 清理过期数据

```http
POST /api/v1/system/cleanup/
```

**请求体**:
```json
{
  "days": 30,
  "types": ["logs", "temp_files", "old_results"]
}
```

## WebSocket API

### 实时任务状态

连接到 WebSocket 获取实时任务执行状态：

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/tasks/');

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Task update:', data);
};

// 订阅特定任务
ws.send(JSON.stringify({
    'action': 'subscribe',
    'task_id': 1
}));
```

## 错误代码

| 状态码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 401 | 未认证 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 409 | 资源冲突 |
| 422 | 数据验证失败 |
| 500 | 服务器内部错误 |

## 限流规则

- **匿名用户**: 100 请求/小时
- **认证用户**: 1000 请求/小时
- **管理员**: 5000 请求/小时

## SDK 和示例

### Python SDK

```python
import requests

class MultiProtGatherAPI:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.headers = {
            'Authorization': f'Token {token}',
            'Content-Type': 'application/json'
        }
    
    def get_devices(self, **params):
        response = requests.get(
            f'{self.base_url}/devices/',
            headers=self.headers,
            params=params
        )
        return response.json()
    
    def create_task(self, data):
        response = requests.post(
            f'{self.base_url}/tasks/',
            headers=self.headers,
            json=data
        )
        return response.json()

# 使用示例
api = MultiProtGatherAPI('http://localhost:8000/api/v1', 'your-token')

# 获取设备列表
devices = api.get_devices(protocol='ssh')

# 创建采集任务
task = api.create_task({
    'name': '测试任务',
    'device_ids': [1, 2],
    'commands': ['show version'],
    'schedule_type': 'immediate'
})
```

### JavaScript SDK

```javascript
class MultiProtGatherAPI {
    constructor(baseUrl, token) {
        this.baseUrl = baseUrl;
        this.headers = {
            'Authorization': `Token ${token}`,
            'Content-Type': 'application/json'
        };
    }

    async request(method, endpoint, data = null) {
        const config = {
            method,
            headers: this.headers
        };

        if (data) {
            config.body = JSON.stringify(data);
        }

        const response = await fetch(`${this.baseUrl}${endpoint}`, config);
        return response.json();
    }

    async getDevices(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.request('GET', `/devices/?${query}`);
    }

    async createTask(data) {
        return this.request('POST', '/tasks/', data);
    }
}

// 使用示例
const api = new MultiProtGatherAPI('http://localhost:8000/api/v1', 'your-token');

// 获取设备列表
api.getDevices({ protocol: 'ssh' })
    .then(response => console.log(response.data));

// 创建任务
api.createTask({
    name: '测试任务',
    device_ids: [1, 2],
    commands: ['show version'],
    schedule_type: 'immediate'
}).then(response => console.log(response));
```

## 最佳实践

### 1. 认证和安全

- 定期轮换 API Token
- 使用 HTTPS 加密传输
- 实施 IP 白名单限制
- 记录 API 访问日志

### 2. 性能优化

- 使用分页避免大量数据传输
- 实施客户端缓存策略
- 合理使用查询参数过滤数据
- 避免频繁的轮询请求

### 3. 错误处理

- 实施重试机制
- 记录详细的错误日志
- 提供友好的错误信息
- 监控 API 响应时间

### 4. 数据管理

- 定期清理过期数据
- 实施数据备份策略
- 监控数据库性能
- 优化查询语句

## 支持和反馈

如果您在使用 API 过程中遇到问题或有改进建议，请：

1. 查看 API 文档和示例
2. 检查请求格式和参数
3. 查看错误日志和响应信息
4. 联系技术支持团队

---

**注意**: 本文档基于 API v1 版本编写，请确保使用正确的 API 版本。API 可能会根据需求进行更新，请关注版本变更说明。
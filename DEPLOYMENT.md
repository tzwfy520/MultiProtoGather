# MultiProtGather 部署指南

本文档详细介绍了 MultiProtGather 系统在生产环境中的部署步骤和配置。

## 系统要求

### 硬件要求

**最低配置**:
- CPU: 2核心
- 内存: 4GB RAM
- 存储: 20GB 可用空间
- 网络: 100Mbps

**推荐配置**:
- CPU: 4核心或更多
- 内存: 8GB RAM 或更多
- 存储: 50GB SSD
- 网络: 1Gbps

### 软件要求

- **操作系统**: Ubuntu 20.04+ / CentOS 8+ / RHEL 8+
- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **Git**: 2.0+

## 部署前准备

### 1. 服务器环境准备

```bash
# 更新系统包
sudo apt update && sudo apt upgrade -y

# 安装必要工具
sudo apt install -y curl wget git vim htop

# 安装 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 安装 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 将用户添加到 docker 组
sudo usermod -aG docker $USER
newgrp docker

# 验证安装
docker --version
docker-compose --version
```

### 2. 防火墙配置

```bash
# Ubuntu/Debian
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable

# CentOS/RHEL
sudo firewall-cmd --permanent --add-port=22/tcp
sudo firewall-cmd --permanent --add-port=80/tcp
sudo firewall-cmd --permanent --add-port=443/tcp
sudo firewall-cmd --reload
```

### 3. 创建部署目录

```bash
# 创建应用目录
sudo mkdir -p /opt/multiprotgather
sudo chown $USER:$USER /opt/multiprotgather
cd /opt/multiprotgather
```

## 部署步骤

### 1. 获取源代码

```bash
# 克隆项目
git clone <repository-url> .

# 或者下载发布版本
wget https://github.com/your-org/multiprotgather/archive/v1.0.0.tar.gz
tar -xzf v1.0.0.tar.gz --strip-components=1
```

### 2. 配置环境变量

```bash
# 复制环境配置模板
cp .env.example .env

# 编辑配置文件
vim .env
```

**重要配置项**:

```bash
# 安全配置
SECRET_KEY=your-very-long-and-random-secret-key-here
DEBUG=False

# 数据库配置
POSTGRES_DB=multiprotgather
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-secure-database-password

# 域名配置
ALLOWED_HOSTS=your-domain.com,www.your-domain.com,localhost
CORS_ALLOWED_ORIGINS=https://your-domain.com,https://www.your-domain.com

# 邮件配置（可选）
EMAIL_HOST=smtp.your-provider.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=noreply@your-domain.com
EMAIL_HOST_PASSWORD=your-email-password

# 监控配置
FLOWER_BASIC_AUTH=admin:your-flower-password
```

### 3. SSL 证书配置（推荐）

#### 使用 Let's Encrypt

```bash
# 安装 Certbot
sudo apt install -y certbot

# 获取证书（需要先停止可能占用80端口的服务）
sudo certbot certonly --standalone -d your-domain.com -d www.your-domain.com

# 证书文件位置
# /etc/letsencrypt/live/your-domain.com/fullchain.pem
# /etc/letsencrypt/live/your-domain.com/privkey.pem
```

#### 修改 Nginx 配置

创建 `nginx-ssl.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    # 日志格式
    log_format  main  '$remote_addr - $remote_user [$time_local] "$request" '
                      '$status $body_bytes_sent "$http_referer" '
                      '"$http_user_agent" "$http_x_forwarded_for"';

    access_log  /var/log/nginx/access.log  main;
    error_log   /var/log/nginx/error.log;

    # 基本设置
    sendfile        on;
    tcp_nopush      on;
    tcp_nodelay     on;
    keepalive_timeout  65;
    types_hash_max_size 2048;
    client_max_body_size 100M;

    # Gzip压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/atom+xml
        image/svg+xml;

    # HTTP 重定向到 HTTPS
    server {
        listen 80;
        server_name your-domain.com www.your-domain.com;
        return 301 https://$server_name$request_uri;
    }

    # HTTPS 服务器
    server {
        listen 443 ssl http2;
        server_name your-domain.com www.your-domain.com;
        root /usr/share/nginx/html;
        index index.html index.htm;

        # SSL 配置
        ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
        ssl_prefer_server_ciphers off;

        # 安全头
        add_header Strict-Transport-Security "max-age=63072000" always;
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header Referrer-Policy "no-referrer-when-downgrade" always;

        # 静态资源缓存
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }

        # API代理
        location /api/ {
            proxy_pass http://backend:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_connect_timeout 30s;
            proxy_send_timeout 30s;
            proxy_read_timeout 30s;
        }

        # React路由支持
        location / {
            try_files $uri $uri/ /index.html;
        }

        # 健康检查
        location /health {
            access_log off;
            return 200 "healthy\n";
            add_header Content-Type text/plain;
        }
    }
}
```

### 4. 修改 Docker Compose 配置

创建生产环境的 `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    container_name: multiprotgather-db
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
      - ./backups:/backups
    networks:
      - multiprotgather-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    container_name: multiprotgather-redis
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    networks:
      - multiprotgather-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "--no-auth-warning", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  backend:
    build:
      context: ./multiprotgather-backend
      dockerfile: Dockerfile
    container_name: multiprotgather-backend
    env_file: .env
    volumes:
      - ./logs:/app/logs
      - ./media:/app/media
      - ./backups:/app/backups
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - multiprotgather-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health/"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build:
      context: ./multiprotgather-frontend
      dockerfile: Dockerfile
    container_name: multiprotgather-frontend
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /etc/letsencrypt:/etc/letsencrypt:ro
      - ./nginx-ssl.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - backend
    networks:
      - multiprotgather-network
    restart: unless-stopped

  celery-worker:
    build:
      context: ./multiprotgather-backend
      dockerfile: Dockerfile
    container_name: multiprotgather-celery-worker
    command: celery -A multiprotgather worker -l info --concurrency=4
    env_file: .env
    volumes:
      - ./logs:/app/logs
      - ./media:/app/media
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - multiprotgather-network
    restart: unless-stopped

  celery-beat:
    build:
      context: ./multiprotgather-backend
      dockerfile: Dockerfile
    container_name: multiprotgather-celery-beat
    command: celery -A multiprotgather beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    env_file: .env
    volumes:
      - ./logs:/app/logs
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - multiprotgather-network
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:

networks:
  multiprotgather-network:
    driver: bridge
```

### 5. 启动服务

```bash
# 构建并启动服务
docker-compose -f docker-compose.prod.yml up -d --build

# 查看服务状态
docker-compose -f docker-compose.prod.yml ps

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f
```

### 6. 初始化应用

```bash
# 等待服务启动完成
sleep 30

# 执行数据库迁移
docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate

# 创建超级用户
docker-compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser

# 收集静态文件
docker-compose -f docker-compose.prod.yml exec backend python manage.py collectstatic --noinput

# 加载初始数据（可选）
docker-compose -f docker-compose.prod.yml exec backend python manage.py loaddata fixtures/initial_data.json
```

## 监控和维护

### 1. 日志管理

```bash
# 创建日志轮转配置
sudo tee /etc/logrotate.d/multiprotgather << EOF
/opt/multiprotgather/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 root root
    postrotate
        docker-compose -f /opt/multiprotgather/docker-compose.prod.yml restart backend celery-worker celery-beat
    endscript
}
EOF
```

### 2. 数据备份

创建备份脚本 `backup.sh`:

```bash
#!/bin/bash

BACKUP_DIR="/opt/multiprotgather/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_BACKUP_FILE="db_backup_${DATE}.sql"
MEDIA_BACKUP_FILE="media_backup_${DATE}.tar.gz"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 数据库备份
docker-compose -f /opt/multiprotgather/docker-compose.prod.yml exec -T db pg_dump -U postgres multiprotgather > $BACKUP_DIR/$DB_BACKUP_FILE

# 媒体文件备份
tar -czf $BACKUP_DIR/$MEDIA_BACKUP_FILE -C /opt/multiprotgather media/

# 删除30天前的备份
find $BACKUP_DIR -name "*.sql" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "Backup completed: $DB_BACKUP_FILE, $MEDIA_BACKUP_FILE"
```

设置定时备份:

```bash
# 添加到 crontab
crontab -e

# 每天凌晨2点备份
0 2 * * * /opt/multiprotgather/backup.sh >> /var/log/multiprotgather-backup.log 2>&1
```

### 3. 系统监控

创建监控脚本 `monitor.sh`:

```bash
#!/bin/bash

COMPOSE_FILE="/opt/multiprotgather/docker-compose.prod.yml"

# 检查服务状态
check_service() {
    local service=$1
    local status=$(docker-compose -f $COMPOSE_FILE ps -q $service)
    
    if [ -z "$status" ]; then
        echo "Service $service is not running"
        return 1
    else
        echo "Service $service is running"
        return 0
    fi
}

# 检查所有服务
services=("db" "redis" "backend" "frontend" "celery-worker" "celery-beat")

for service in "${services[@]}"; do
    if ! check_service $service; then
        echo "Restarting $service..."
        docker-compose -f $COMPOSE_FILE restart $service
    fi
done

# 检查磁盘空间
disk_usage=$(df /opt/multiprotgather | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $disk_usage -gt 80 ]; then
    echo "Warning: Disk usage is ${disk_usage}%"
fi

# 检查内存使用
memory_usage=$(free | awk 'NR==2{printf "%.2f", $3*100/$2}')
if (( $(echo "$memory_usage > 80" | bc -l) )); then
    echo "Warning: Memory usage is ${memory_usage}%"
fi
```

### 4. SSL 证书自动续期

```bash
# 创建续期脚本
sudo tee /opt/multiprotgather/renew-ssl.sh << EOF
#!/bin/bash
certbot renew --quiet
if [ $? -eq 0 ]; then
    docker-compose -f /opt/multiprotgather/docker-compose.prod.yml restart frontend
fi
EOF

sudo chmod +x /opt/multiprotgather/renew-ssl.sh

# 添加到 crontab（每月1号检查）
echo "0 3 1 * * /opt/multiprotgather/renew-ssl.sh" | sudo crontab -
```

## 更新部署

### 1. 应用更新

```bash
cd /opt/multiprotgather

# 备份当前版本
git stash
git pull origin main

# 重新构建并启动
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build

# 执行数据库迁移
docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate

# 收集静态文件
docker-compose -f docker-compose.prod.yml exec backend python manage.py collectstatic --noinput
```

### 2. 回滚操作

```bash
# 查看提交历史
git log --oneline -10

# 回滚到指定版本
git reset --hard <commit-hash>

# 重新部署
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build
```

## 故障排除

### 1. 常见问题

**服务无法启动**:
```bash
# 查看详细日志
docker-compose -f docker-compose.prod.yml logs [service_name]

# 检查端口占用
netstat -tlnp | grep :80
netstat -tlnp | grep :443

# 检查磁盘空间
df -h
```

**数据库连接失败**:
```bash
# 检查数据库服务
docker-compose -f docker-compose.prod.yml exec db psql -U postgres -c "\l"

# 检查网络连接
docker-compose -f docker-compose.prod.yml exec backend ping db
```

**前端无法访问**:
```bash
# 检查 Nginx 配置
docker-compose -f docker-compose.prod.yml exec frontend nginx -t

# 重新加载配置
docker-compose -f docker-compose.prod.yml restart frontend
```

### 2. 性能优化

**数据库优化**:
```sql
-- 添加索引
CREATE INDEX CONCURRENTLY idx_devices_ip_address ON devices_device(ip_address);
CREATE INDEX CONCURRENTLY idx_tasks_status ON tasks_task(status);
CREATE INDEX CONCURRENTLY idx_results_created_at ON results_result(created_at);

-- 分析表统计信息
ANALYZE;
```

**应用优化**:
```bash
# 增加 Celery Worker 数量
docker-compose -f docker-compose.prod.yml scale celery-worker=4

# 调整数据库连接池
# 在 Django settings 中配置 DATABASES['default']['CONN_MAX_AGE']
```

## 安全建议

1. **定期更新系统和依赖**
2. **使用强密码和密钥**
3. **启用防火墙和入侵检测**
4. **定期备份数据**
5. **监控系统日志**
6. **限制管理员访问**
7. **使用 HTTPS 加密传输**

## 支持和联系

如果在部署过程中遇到问题，请：

1. 查看项目文档和 FAQ
2. 检查 GitHub Issues
3. 联系技术支持团队

---

**注意**: 本文档假设您具有基本的 Linux 系统管理和 Docker 使用经验。在生产环境部署前，请确保充分测试所有配置。
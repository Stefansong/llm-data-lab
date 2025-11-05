# 🐳 Docker 部署指南

本指南介绍如何使用 Docker 和 Docker Compose 部署 LLM Data Lab 项目。

## 📋 前置要求

### 系统要求
- Docker Engine 20.10+
- Docker Compose 2.0+
- 至少 4GB 可用内存
- 至少 10GB 可用磁盘空间

### 安装 Docker

**macOS:**
```bash
brew install --cask docker
# 或下载 Docker Desktop: https://www.docker.com/products/docker-desktop
```

**Linux (Ubuntu/Debian):**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

**Windows:**
- 下载并安装 Docker Desktop: https://www.docker.com/products/docker-desktop

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/Stefansong/llm-data-lab.git
cd llm-data-lab
```

### 2. 配置环境变量

```bash
# 复制环境变量示例文件
cp backend/.env.example backend/.env

# 编辑 .env 文件，填入你的 API Keys
vim backend/.env  # 或使用其他编辑器
```

**必须配置的变量：**
```bash
# 安全密钥（生产环境必须修改！）
JWT_SECRET_KEY=your-super-secret-key-change-this
CREDENTIALS_SECRET_KEY=your-credentials-encryption-key

# 至少配置一个 LLM API Key
OPENAI_API_KEY=sk-...
# 或
ANTHROPIC_API_KEY=sk-ant-...
# 或其他模型的 API Key
```

### 3. 启动服务

```bash
# 构建并启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 查看服务状态
docker-compose ps
```

### 4. 访问应用

- **前端**: http://localhost:3000
- **后端 API 文档**: http://localhost:8000/docs
- **后端健康检查**: http://localhost:8000/health

## 📊 Docker Compose 架构

```
┌─────────────────────────────────────────┐
│          LLM Data Lab                   │
├─────────────────────────────────────────┤
│                                         │
│  ┌──────────────┐    ┌──────────────┐  │
│  │   Frontend   │───▶│   Backend    │  │
│  │  (Next.js)   │    │  (FastAPI)   │  │
│  │  Port: 3000  │    │  Port: 8000  │  │
│  └──────────────┘    └──────────────┘  │
│                             │           │
│                             ▼           │
│                      ┌──────────────┐  │
│                      │   Database   │  │
│                      │   (SQLite)   │  │
│                      └──────────────┘  │
│                                         │
└─────────────────────────────────────────┘
```

## 🔧 常用命令

### 服务管理

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看日志
docker-compose logs -f [service_name]

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f frontend
```

### 构建和更新

```bash
# 重新构建镜像
docker-compose build

# 重新构建并启动
docker-compose up -d --build

# 拉取最新镜像
docker-compose pull

# 强制重新创建容器
docker-compose up -d --force-recreate
```

### 数据管理

```bash
# 查看数据卷
docker volume ls

# 备份数据库
docker-compose exec backend cat /app/llm_data_lab.db > backup.db

# 恢复数据库
docker-compose exec -T backend sh -c 'cat > /app/llm_data_lab.db' < backup.db

# 清理未使用的数据卷
docker volume prune
```

### 调试

```bash
# 进入后端容器
docker-compose exec backend bash

# 进入前端容器
docker-compose exec frontend sh

# 查看容器资源使用情况
docker stats

# 检查容器健康状态
docker-compose ps
```

## 🔒 生产环境部署

### 1. 安全配置

**修改默认密钥：**
```bash
# 生成安全的密钥
openssl rand -hex 32

# 在 .env 中使用生成的密钥
JWT_SECRET_KEY=<生成的密钥>
CREDENTIALS_SECRET_KEY=<另一个生成的密钥>
```

### 2. 使用 HTTPS

**使用 Nginx 反向代理：**

```yaml
# docker-compose.prod.yml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - frontend
      - backend
```

**Nginx 配置示例：**
```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    location / {
        proxy_pass http://frontend:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 3. 资源限制

在 `docker-compose.yml` 中添加资源限制：

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

### 4. 使用外部数据库（推荐）

```yaml
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: llm_data_lab
      POSTGRES_USER: llm_user
      POSTGRES_PASSWORD: secure_password
    volumes:
      - postgres-data:/var/lib/postgresql/data

  backend:
    environment:
      - DATABASE_URL=postgresql://llm_user:secure_password@postgres/llm_data_lab
```

## 🐛 故障排查

### 端口占用

```bash
# 检查端口占用
lsof -i :3000
lsof -i :8000

# 修改端口（在 docker-compose.yml 中）
ports:
  - "3001:3000"  # 前端
  - "8001:8000"  # 后端
```

### 容器无法启动

```bash
# 查看详细日志
docker-compose logs backend
docker-compose logs frontend

# 检查容器状态
docker-compose ps

# 重新构建
docker-compose build --no-cache
docker-compose up -d
```

### 数据库连接问题

```bash
# 检查数据库文件权限
docker-compose exec backend ls -la /app/llm_data_lab.db

# 重新创建数据库
docker-compose exec backend rm /app/llm_data_lab.db
docker-compose restart backend
```

### 前端无法连接后端

1. 检查 `NEXT_PUBLIC_API_BASE_URL` 配置
2. 确认后端健康检查通过：`curl http://localhost:8000/docs`
3. 查看网络连接：`docker network inspect llm-data-lab_llm-data-lab-network`

## 📈 性能优化

### 1. 使用多阶段构建（已实现）

前端 Dockerfile 使用三阶段构建，减小镜像体积。

### 2. 启用 BuildKit

```bash
# 启用 Docker BuildKit（更快的构建）
export DOCKER_BUILDKIT=1
docker-compose build
```

### 3. 使用镜像缓存

```bash
# 使用缓存加速构建
docker-compose build --pull
```

### 4. 资源监控

```bash
# 实时监控资源使用
docker stats

# 使用 cAdvisor 进行详细监控
docker run -d -p 8080:8080 \
  -v /:/rootfs:ro \
  -v /var/run:/var/run:ro \
  -v /sys:/sys:ro \
  google/cadvisor:latest
```

## 🔄 更新和维护

### 更新应用代码

```bash
# 1. 拉取最新代码
git pull origin main

# 2. 重新构建并启动
docker-compose up -d --build

# 3. 清理旧镜像
docker image prune -f
```

### 定期备份

```bash
# 创建备份脚本
cat > backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="./backups"
mkdir -p $BACKUP_DIR

# 备份数据库
docker-compose exec -T backend cat /app/llm_data_lab.db > $BACKUP_DIR/db_$DATE.db

# 备份用户数据
tar -czf $BACKUP_DIR/data_$DATE.tar.gz uploaded_datasets/ analysis_artifacts/

echo "备份完成: $BACKUP_DIR"
EOF

chmod +x backup.sh
./backup.sh
```

## ❓ 常见问题

**Q: 如何修改端口？**  
A: 编辑 `docker-compose.yml` 的 `ports` 部分。

**Q: 如何查看容器内文件？**  
A: 使用 `docker-compose exec backend ls /app`

**Q: 如何清理所有容器和数据？**  
A: `docker-compose down -v` （⚠️ 会删除所有数据！）

**Q: 如何使用 GPU 加速？**  
A: 需要安装 NVIDIA Docker 运行时，并在 docker-compose.yml 中配置 GPU 支持。

## 📚 更多资源

- [Docker 官方文档](https://docs.docker.com/)
- [Docker Compose 文档](https://docs.docker.com/compose/)
- [项目 GitHub](https://github.com/Stefansong/llm-data-lab)
- [问题反馈](https://github.com/Stefansong/llm-data-lab/issues)

---

**祝你部署顺利！** 🎉

如遇问题，欢迎提交 Issue 或查看项目文档。


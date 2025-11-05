# 🚀 腾讯云服务器部署检查清单

本文档提供完整的腾讯云服务器部署步骤和检查清单。

## ✅ 部署前检查

### 本地准备
- [x] 所有代码已提交到 Git
- [x] frontend/lib/ 文件已添加（6 个文件）
- [x] 腾讯云镜像源已配置
- [x] public/.gitkeep 已创建
- [ ] 已推送到 GitHub：`git push origin main`

### 服务器要求
- [ ] 已购买腾讯云服务器（2核4GB 或以上）
- [ ] 已安装 Docker 和 Docker Compose
- [ ] 已配置安全组（开放 3000, 8000, 22 端口）
- [ ] 已获取服务器 IP 地址

---

## 📝 详细部署步骤

### 第一步：连接到服务器

```bash
ssh root@你的腾讯云服务器IP
```

### 第二步：安装 Docker（如果还没有）

```bash
# 安装 Docker
curl -fsSL https://get.docker.com | bash

# 安装 Docker Compose
apt install docker-compose -y

# 启动 Docker
systemctl start docker
systemctl enable docker

# 验证安装
docker --version
docker-compose --version
```

### 第三步：克隆项目

```bash
# 克隆代码
git clone https://github.com/Stefansong/llm-data-lab.git

# 进入目录
cd llm-data-lab

# 验证文件完整性
ls -la frontend/lib/
# 应该看到：api.ts, authToken.ts, i18n.ts, providerSettings.ts, userProfile.ts

ls -la frontend/public/
# 应该看到：.gitkeep
```

### 第四步：配置环境变量

```bash
# 复制示例文件
cp backend/.env.example backend/.env

# 生成安全密钥
echo "JWT_SECRET_KEY=$(openssl rand -hex 32)"

# 编辑配置文件
nano backend/.env
```

**必须配置的内容**：

```bash
# 安全密钥（使用上面生成的）
JWT_SECRET_KEY=<粘贴生成的64字符密钥>

# 至少配置一个 LLM API Key
OPENAI_API_KEY=sk-...
# 或
DEEPSEEK_API_KEY=sk-...
# 或其他模型的 API Key
```

### 第五步：部署服务

**方式 1：使用一键部署脚本（推荐）**

```bash
bash deploy-server.sh
```

**方式 2：手动部署**

```bash
# 清理环境
docker-compose down -v
docker system prune -f

# 构建镜像
docker-compose build --no-cache

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

### 第六步：验证部署

```bash
# 查看服务状态
docker-compose ps

# 应该看到两个服务都在运行：
# llm-data-lab-backend    Up (healthy)
# llm-data-lab-frontend   Up

# 测试后端
curl http://localhost:8000/docs

# 测试前端
curl http://localhost:3000
```

### 第七步：配置防火墙和安全组

**腾讯云控制台操作**：
1. 进入"云服务器" → "安全组"
2. 添加入站规则：
   - `3000/TCP` - 前端访问
   - `8000/TCP` - 后端 API
   - `22/TCP` - SSH（已有）
   - `80/TCP` - HTTP（可选）
   - `443/TCP` - HTTPS（可选）

### 第八步：访问应用

浏览器打开：
- 前端：`http://你的服务器IP:3000`
- 后端 API 文档：`http://你的服务器IP:8000/docs`

---

## 🔧 常用运维命令

### 服务管理
```bash
# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 重启服务
docker-compose restart

# 停止服务
docker-compose down

# 更新代码并重启
git pull origin main
docker-compose up -d --build
```

### 备份数据
```bash
# 备份数据库
docker-compose exec backend cat /app/db/llm_data_lab.db > backup.db

# 备份用户数据
tar -czf backup-data.tar.gz uploaded_datasets/ analysis_artifacts/
```

### 查看资源使用
```bash
# 查看容器资源
docker stats

# 查看磁盘使用
df -h

# 查看内存使用
free -h
```

---

## ⚠️ 故障排查

### 问题 1：后端启动失败

```bash
# 查看详细日志
docker logs llm-data-lab-backend

# 常见原因：
# - JWT_SECRET_KEY 未配置或太短
# - 端口 8000 被占用
# - 环境变量格式错误
```

### 问题 2：前端无法访问后端

```bash
# 检查网络连接
docker network inspect llm_stats_web_llm-data-lab-network

# 检查后端是否健康
curl http://localhost:8000/docs
```

### 问题 3：镜像构建超时

```bash
# 增加 Docker 构建超时
export COMPOSE_HTTP_TIMEOUT=300
docker-compose build --no-cache
```

---

## 🎯 生产环境优化（可选）

### 配置 Nginx 反向代理

```bash
# 安装 Nginx
apt install nginx -y

# 配置反向代理
cat > /etc/nginx/sites-available/llm-data-lab << 'NGINX_EOF'
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    client_max_body_size 100M;
}
NGINX_EOF

# 启用配置
ln -s /etc/nginx/sites-available/llm-data-lab /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

### 配置 HTTPS（Let's Encrypt）

```bash
# 安装 Certbot
apt install certbot python3-certbot-nginx -y

# 申请证书
certbot --nginx -d your-domain.com

# 自动续期
certbot renew --dry-run
```

---

## 📞 技术支持

- GitHub Issues: https://github.com/Stefansong/llm-data-lab/issues
- 文档：查看项目根目录的 DOCKER_DEPLOY.md

---

**祝部署顺利！** 🎉

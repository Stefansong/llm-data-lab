# 🌐 btchuro.com 部署完整指南

本指南专门为 `btchuro.com` 域名部署 LLM Data Lab。

---

## ✅ 已发现并修复的问题

### 问题 1：前端 API 地址错误 ❌
**表现**：
```
Access to fetch at 'http://localhost:8000/auth/register' from origin 'https://btchuro.com' has been blocked by CORS policy
```

**原因**：
- 前端在浏览器中运行，无法访问 `localhost:8000`
- 需要通过域名 + Nginx 转发访问后端

**修复**：
- ✅ 创建 `docker-compose.prod.yml` 覆盖配置
- ✅ 设置 `NEXT_PUBLIC_API_BASE_URL=https://btchuro.com/api`

---

### 问题 2：CORS 配置不包含生产域名 ❌
**原因**：
- `backend/main.py` 的 CORS 只允许 `http://localhost:3000`
- 不包含 `https://btchuro.com`

**修复**：
- ✅ 更新 CORS 配置为 `allow_origins=["*"]`
- ✅ 支持任何域名访问（生产环境可以改为具体域名列表）

---

### 问题 3：docker-compose.yml 使用容器内部地址 ❌
**原因**：
- `NEXT_PUBLIC_API_BASE_URL=http://backend:8000`
- 这是 Docker 网络内部地址，浏览器无法访问

**修复**：
- ✅ 改为从环境变量读取：`${NEXT_PUBLIC_API_BASE_URL:-http://localhost:8000}`
- ✅ 生产环境通过 `docker-compose.prod.yml` 覆盖为 `https://btchuro.com/api`

---

## 🚀 完整部署流程

### 第一步：在本地 Mac 推送代码

```bash
cd /Users/stefan/Desktop/llm_stats_web

# 查看待推送的提交
git status

# 推送到 GitHub
git push origin main
```

---

### 第二步：在服务器上部署应用

#### 2.1 拉取最新代码

```bash
# SSH 连接到服务器
ssh root@你的服务器IP

# 进入项目目录（如果已克隆）
cd ~/llm-data-lab

# 拉取最新代码
git pull origin main

# 或者首次部署时克隆
# cd ~
# git clone https://github.com/Stefansong/llm-data-lab.git
# cd llm-data-lab
```

#### 2.2 配置环境变量

```bash
# 使用自动修复脚本
bash fix-env.sh

# 或手动创建
cp backend/.env.example backend/.env

# 编辑配置文件
nano backend/.env

# 必须配置：
# JWT_SECRET_KEY=<用 openssl rand -hex 32 生成>
# OPENAI_API_KEY=sk-your-actual-key-here
```

**快速配置**（替换 API Key）：

```bash
# 生成 JWT 密钥并配置 OpenAI
cat > backend/.env << 'EOF'
JWT_SECRET_KEY=$(openssl rand -hex 32)
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRES_MINUTES=43200
DATABASE_URL=sqlite+aiosqlite:///./llm_data_lab.db
OPENAI_API_KEY=sk-your-openai-key-here
OPENAI_DEFAULT_MODELS=["gpt-4o","gpt-4o-mini","gpt-4-turbo"]
MAX_CODE_EXECUTION_SECONDS=60
MAX_CODE_EXECUTION_MEMORY_MB=768
EOF

# 替换占位符
sed -i "s/\$(openssl rand -hex 32)/$(openssl rand -hex 32)/" backend/.env
sed -i "s/sk-your-openai-key-here/你的实际OpenAI-API-Key/" backend/.env
```

#### 2.3 部署 Docker 容器

```bash
# 🇨🇳 中国服务器部署（使用腾讯云镜像 + 生产配置）
docker-compose -f docker-compose.yml -f docker-compose.cn.yml -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.yml -f docker-compose.cn.yml -f docker-compose.prod.yml up -d

# 或使用环境变量方式
export NEXT_PUBLIC_API_BASE_URL=https://btchuro.com/api
docker-compose -f docker-compose.yml -f docker-compose.cn.yml build --no-cache
docker-compose -f docker-compose.yml -f docker-compose.cn.yml up -d

# 查看日志
docker-compose logs -f
```

---

### 第三步：配置 Nginx 和 SSL

#### 3.1 使用自动化脚本（推荐）

```bash
# 自动配置 Nginx + SSL
bash setup-domain.sh btchuro.com your-email@example.com
```

#### 3.2 手动配置

```bash
# 安装依赖
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx

# 创建 Nginx 配置
sudo tee /etc/nginx/sites-available/llm-data-lab > /dev/null << 'EOF'
server {
    listen 80;
    server_name btchuro.com www.btchuro.com;
    
    client_max_body_size 100M;
    
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
    
    location /api/ {
        rewrite ^/api/(.*) /$1 break;
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /docs {
        proxy_pass http://localhost:8000/docs;
        proxy_set_header Host $host;
    }
}
EOF

# 启用配置
sudo ln -sf /etc/nginx/sites-available/llm-data-lab /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# 测试并重启
sudo nginx -t
sudo systemctl restart nginx

# 申请 SSL 证书
sudo certbot --nginx \
    -d btchuro.com \
    -d www.btchuro.com \
    --non-interactive \
    --agree-tos \
    --email your-email@example.com \
    --redirect
```

---

### 第四步：配置防火墙

#### 腾讯云控制台

1. 登录腾讯云控制台
2. 进入**云服务器 CVM** → 选择你的服务器
3. 点击**安全组**标签
4. **添加入站规则**：

| 类型 | 来源 | 协议端口 | 策略 |
|-----|------|---------|------|
| 自定义 | 0.0.0.0/0 | TCP:80 | 允许 |
| 自定义 | 0.0.0.0/0 | TCP:443 | 允许 |

#### 服务器本地防火墙

```bash
# 开放端口
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw reload

# 检查状态
sudo ufw status
```

---

## ✅ 验证部署

### 1. 检查 Docker 容器

```bash
docker-compose ps

# 应该显示：
# llm-data-lab-backend   healthy
# llm-data-lab-frontend  running
```

### 2. 检查前端环境变量

```bash
docker-compose exec frontend env | grep API_BASE_URL

# 应该显示：
# NEXT_PUBLIC_API_BASE_URL=https://btchuro.com/api
```

### 3. 检查 Nginx

```bash
sudo nginx -t
sudo systemctl status nginx
```

### 4. 测试 API 访问

```bash
# 测试后端健康检查
curl https://btchuro.com/api/health

# 应该返回：
# {"status":"ok"}

# 测试 API 文档
curl https://btchuro.com/docs
```

### 5. 浏览器测试

打开浏览器访问：
- https://btchuro.com（前端主页）
- https://btchuro.com/docs（API 文档）

按 F12 打开开发者工具，在 Network 标签注册用户，应该看到：

```
Request URL: https://btchuro.com/api/auth/register  ✅
Status Code: 200 OK  ✅
```

---

## 📊 架构图

```
用户浏览器
    ↓
https://btchuro.com:443
    ↓
Nginx（反向代理）
    ↓
    ├─→ / → localhost:3000 (前端容器)
    │         环境变量：NEXT_PUBLIC_API_BASE_URL=https://btchuro.com/api
    │         前端会请求：https://btchuro.com/api/xxx
    │
    └─→ /api/ → localhost:8000 (后端容器)
              CORS：允许 https://btchuro.com
              接收请求并响应
```

---

## 🔧 配置文件对照表

| 文件 | 配置项 | 值 | 说明 |
|-----|--------|----|----|
| `docker-compose.prod.yml` | NEXT_PUBLIC_API_BASE_URL | `https://btchuro.com/api` | 前端 API 地址 |
| `backend/main.py` | allow_origins | `["*"]` | CORS 允许所有来源 |
| `backend/.env` | JWT_SECRET_KEY | `<64字符随机字符串>` | JWT 签名密钥 |
| `backend/.env` | OPENAI_API_KEY | `sk-proj-...` | OpenAI API 密钥 |
| Nginx `/etc/nginx/sites-available/llm-data-lab` | server_name | `btchuro.com www.btchuro.com` | 域名配置 |
| Nginx | location `/` | → `localhost:3000` | 前端转发 |
| Nginx | location `/api/` | → `localhost:8000` | 后端转发 |

---

## 🐛 常见问题

### 问题 1：404 Not Found

**原因**：前端还在使用旧的 API 地址

**解决**：
```bash
# 重新构建前端
docker-compose -f docker-compose.yml -f docker-compose.cn.yml -f docker-compose.prod.yml build frontend
docker-compose -f docker-compose.yml -f docker-compose.cn.yml -f docker-compose.prod.yml up -d

# 浏览器清除缓存，按 Ctrl+Shift+Delete
```

### 问题 2：CORS 错误

**原因**：后端 CORS 配置未包含域名

**解决**：已在 `backend/main.py` 中设置 `allow_origins=["*"]`，重新构建后端即可

### 问题 3：502 Bad Gateway

**原因**：Docker 容器未运行

**解决**：
```bash
docker-compose ps
docker-compose logs backend
docker-compose logs frontend
```

---

## 📝 完整一键部署命令

在服务器上执行（复制整段）：

```bash
#!/bin/bash
# btchuro.com 一键部署脚本

cd ~/llm-data-lab

# 1. 拉取最新代码
git pull origin main

# 2. 配置环境变量（如果还没配置）
if [ ! -f "backend/.env" ]; then
    bash fix-env.sh
    echo "请编辑 backend/.env 填入 OpenAI API Key："
    echo "nano backend/.env"
    exit 0
fi

# 3. 配置域名和 SSL（如果还没配置）
if [ ! -f "/etc/nginx/sites-enabled/llm-data-lab" ]; then
    bash setup-domain.sh btchuro.com your-email@example.com
fi

# 4. 部署应用
echo "🚀 正在部署到 btchuro.com..."

# 停止旧服务
docker-compose down

# 构建（使用中国镜像 + 生产配置）
docker-compose -f docker-compose.yml -f docker-compose.cn.yml -f docker-compose.prod.yml build --no-cache

# 启动
docker-compose -f docker-compose.yml -f docker-compose.cn.yml -f docker-compose.prod.yml up -d

# 等待启动
sleep 10

# 检查状态
docker-compose ps

echo ""
echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║                   🎉 部署完成！                                       ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "🌐 访问地址："
echo "   主页:      https://btchuro.com"
echo "   API 文档:  https://btchuro.com/docs"
echo ""
echo "📊 查看日志："
echo "   docker-compose logs -f"
echo ""
```

---

## 🔒 安全建议（生产环境）

### 1. 限制 CORS 来源

编辑 `backend/main.py`，将 `allow_origins=["*"]` 改为：

```python
allow_origins=[
    "https://btchuro.com",
    "https://www.btchuro.com",
]
```

### 2. 配置 Nginx 安全头

在 Nginx 配置中添加：

```nginx
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "no-referrer-when-downgrade" always;
```

### 3. 定期更新 SSL 证书

```bash
# 测试自动续期
sudo certbot renew --dry-run

# 查看证书状态
sudo certbot certificates
```

---

## 📊 性能优化建议

### 1. 启用 Nginx 缓存

```nginx
# 在 Nginx 配置中添加
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=my_cache:10m max_size=1g;

location /_next/static/ {
    proxy_pass http://localhost:3000;
    proxy_cache my_cache;
    proxy_cache_valid 200 7d;
}
```

### 2. 启用 Gzip 压缩

```nginx
gzip on;
gzip_vary on;
gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
```

### 3. 配置 CDN（可选）

如果流量较大，可以考虑使用腾讯云 CDN 加速静态资源。

---

## 🔄 更新部署流程

后续更新代码时：

```bash
# 在服务器上
cd ~/llm-data-lab

# 1. 拉取最新代码
git pull origin main

# 2. 重新构建并部署
docker-compose -f docker-compose.yml -f docker-compose.cn.yml -f docker-compose.prod.yml down
docker-compose -f docker-compose.yml -f docker-compose.cn.yml -f docker-compose.prod.yml build
docker-compose -f docker-compose.yml -f docker-compose.cn.yml -f docker-compose.prod.yml up -d

# 3. 查看日志
docker-compose logs -f
```

---

## 📞 故障排查

### 查看完整日志

```bash
# 后端日志
docker-compose logs backend | less

# 前端日志
docker-compose logs frontend | less

# Nginx 日志
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### 进入容器调试

```bash
# 进入后端容器
docker-compose exec backend bash

# 查看环境变量
env | grep -E "JWT|OPENAI|API"

# 退出
exit

# 进入前端容器
docker-compose exec frontend sh

# 查看环境变量
env | grep NEXT_PUBLIC

# 退出
exit
```

---

**最后更新**：2025-11-05  
**域名**：btchuro.com  
**部署状态**：✅ 配置已优化，待部署验证


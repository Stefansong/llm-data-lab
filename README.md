# LLM Data Lab

一个面向科研工作者的数据分析协作平台。用户以自然语言描述任务，系统即可调用多种大语言模型生成 Python 代码，在受控沙箱内执行并输出统计结果、图表与文字总结。

## 功能亮点
- **多模型联动**：已适配 OpenAI、Anthropic、DeepSeek、Qwen、SiliconFlow 等 API，便于横向对比不同模型产出的代码与结论。
- **一键执行**：生成的 Python 脚本直接在隔离沙箱中同步运行，产出标准输出、错误日志与图像附件。
- **数据工作台**：集成数据上传、模型选择、代码编辑、执行结果浏览及模型对话协作于一体。
- **历史留存**：所有任务自动归档，可随时查看 prompt、代码、执行日志与生成的附件。
- **多用户隔离**：后端以 `X-User-Id` 头区分用户，上传文件、执行产物、任务记录与会话均按用户单独存储。
- **凭证集中管理**：每个账户的 API Key、Base URL 与模型设置都会加密保存到后端，可在任意设备登录后自动同步。
- **双模式分析**：可选择"分析策略"（生成详细方案）或"数据分析"（直接执行统计/可视化），提示词会随模式自动调整。
- **账户体系**：提供注册、登录与退出功能，所有 API 现需携带 Bearer Token 访问，确保多用户场景下的权限隔离。

## 目录结构
```
llm-data-lab/
├── backend/              # FastAPI 后端服务
│   ├── api/              # REST 接口（LLM、执行、历史、数据集）
│   ├── llm_adapters/     # 多模型 API 适配层实现
│   ├── sandbox/          # Python 代码执行沙箱
│   ├── services/         # 业务逻辑、数据库读写
│   ├── models/           # SQLAlchemy 表定义
│   └── main.py           # FastAPI 应用入口
├── frontend/             # Next.js 14 + Tailwind 前端
│   ├── app/              # App Router 页面（首页、工作台、历史、设置）
│   ├── components/       # UI 组件与业务模块
│   └── lib/api.ts        # 与后端交互的封装
├── prompts/              # 提示词模板（YAML）
└── notebooks/            # 示例分析或研究记录
```

---

## 🚀 快速部署

### 本地开发

#### 后端
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
cp .env.example .env
# 编辑 .env，填入至少一个 LLM API Key
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

#### 前端
```bash
cd frontend
npm install
npm run dev
# 访问 http://localhost:3000
```

---

### Docker 部署（生产环境推荐）

#### 1. 配置环境变量

```bash
# 复制配置模板
cp backend/.env.example backend/.env

# 编辑配置文件
nano backend/.env
```

**必需配置**：
```bash
# 生成 JWT 密钥（至少 32 字符）
JWT_SECRET_KEY=$(openssl rand -hex 32)

# 至少配置一个 LLM API Key
OPENAI_API_KEY=sk-your-openai-key
# 或
DEEPSEEK_API_KEY=sk-your-deepseek-key
```

**完整配置示例**：
```env
# 安全配置
JWT_SECRET_KEY=<使用 openssl rand -hex 32 生成>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRES_MINUTES=43200

# 数据库
DATABASE_URL=sqlite+aiosqlite:///./llm_data_lab.db

# LLM API（至少配置一个）
OPENAI_API_KEY=sk-your-key
OPENAI_DEFAULT_MODELS=["gpt-4o","gpt-4o-mini","gpt-4-turbo"]

# 执行限制
MAX_CODE_EXECUTION_SECONDS=60
MAX_CODE_EXECUTION_MEMORY_MB=768
```

#### 2. 启动服务

```bash
# 本地测试
docker-compose up -d

# 🇨🇳 中国服务器（使用腾讯云镜像加速）
bash deploy.sh start cn

# 🌐 生产环境部署（使用域名访问）
bash deploy.sh start cn prod
```

#### 3. 访问应用

- **本地开发**：http://localhost:3000
- **生产环境**：https://your-domain.com

---

## 🌐 域名配置（生产环境）

### 前置准备

1. 拥有一个域名（例如：`btchuro.com`）
2. 域名已解析到服务器 IP
3. 服务器防火墙开放 80、443 端口

### 自动配置（推荐）

```bash
# 在服务器上执行（替换你的域名和邮箱）
bash deploy.sh domain btchuro.com your-email@example.com
```

这个脚本会自动：
- ✅ 安装 Nginx
- ✅ 配置反向代理
- ✅ 申请免费 SSL 证书（Let's Encrypt）
- ✅ 配置 HTTPS 自动重定向

### 手动配置

#### 1. 安装 Nginx 和 Certbot

```bash
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx
```

#### 2. 创建 Nginx 配置

```bash
sudo nano /etc/nginx/sites-available/llm-data-lab
```

粘贴以下内容（替换 `your-domain.com`）：

```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    
    client_max_body_size 100M;
    
    # 前端
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
    
    # 后端 API
    location /api/ {
        rewrite ^/api/(.*) /$1 break;
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    # API 文档
    location /docs {
        proxy_pass http://localhost:8000/docs;
    }
}
```

#### 3. 启用配置并申请 SSL

```bash
# 启用配置
sudo ln -s /etc/nginx/sites-available/llm-data-lab /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl restart nginx

# 申请免费 SSL 证书
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

#### 4. 更新应用配置

```bash
# 编辑 docker-compose.prod.yml
nano docker-compose.prod.yml
```

修改 API 地址为你的域名：
```yaml
services:
  frontend:
    environment:
      - NEXT_PUBLIC_API_BASE_URL=https://your-domain.com/api
```

#### 5. 重新部署

```bash
bash deploy.sh start cn prod
```

---

## 🔧 常用管理命令

```bash
# 查看服务状态
docker-compose ps

# 查看日志（实时）
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f frontend

# 重启服务
docker-compose restart

# 停止服务
docker-compose down

# 完全清理重建
docker-compose down -v
bash deploy.sh start cn prod
```

---

## 🛠️ 统一部署工具

项目提供一个 **deploy.sh** 脚本，包含所有部署功能：

```bash
# 📦 部署应用
bash deploy.sh start              # 本地/国外服务器
bash deploy.sh start cn           # 中国服务器（镜像加速）
bash deploy.sh start prod         # 生产环境（使用域名）
bash deploy.sh start cn prod      # 中国 + 生产（推荐）

# 🌐 配置域名
bash deploy.sh domain btchuro.com your-email@example.com

# 🔧 修复配置
bash deploy.sh fix-env

# 📖 查看帮助
bash deploy.sh help
```

---

## 🐛 常见问题

### 1. 用户注册失败（CORS 错误）

**症状**：
```
Access to fetch at 'http://localhost:8000/auth/register' has been blocked by CORS policy
```

**原因**：前端 API 地址配置错误

**解决方案**：
```bash
# 方式 1：使用生产配置部署
bash deploy.sh start cn prod

# 方式 2：手动设置环境变量
export NEXT_PUBLIC_API_BASE_URL=https://your-domain.com/api
docker-compose down
docker-compose build frontend
docker-compose up -d
```

### 2. 后端容器启动失败

**症状**：
```
container llm-data-lab-backend is unhealthy
```

**常见原因**：
- JWT_SECRET_KEY 长度不足（需要 ≥32 字符）
- .env 文件配置格式错误
- 缺少 LLM API Key

**解决方案**：
```bash
# 自动修复
bash deploy.sh fix-env

# 查看日志
docker-compose logs backend

# 查看详细诊断
bash diagnose.sh
```

### 3. Docker 构建速度慢

**症状**：apt-get update 或 pip install 耗时很长

**解决方案**：
```bash
# 🇨🇳 中国服务器：使用国内镜像源
bash deploy.sh start cn

# 这会使用腾讯云镜像，构建速度提升 70%
```

### 4. Git 同步冲突

**症状**：
```
error: Your local changes would be overwritten by merge
```

**解决方案**：
```bash
# 在服务器上强制同步
cd ~/llm-data-lab
git fetch origin
git reset --hard origin/main
```

---

## 📦 数据分析能力

后端已预装常用科研分析库：
- **数据处理**：pandas, numpy
- **可视化**：matplotlib, seaborn, plotly
- **统计建模**：scipy, statsmodels, lifelines
- **机器学习**：scikit-learn, shap, prophet
- **贝叶斯与概率建模**：pymc, arviz
- **NLP 与文本处理**：nltk, spacy

可根据需求在 `backend/pyproject.toml` 中扩展。

---

## 🔒 安全配置

### JWT 密钥生成

```bash
# 生成 64 字符的随机密钥
openssl rand -hex 32
```

### CORS 配置（生产环境）

编辑 `backend/main.py`，将：
```python
allow_origins=["*"],
```

改为具体域名：
```python
allow_origins=[
    "https://your-domain.com",
    "https://www.your-domain.com",
],
```

---

## 📊 部署架构

### 本地开发
```
浏览器 → http://localhost:3000 (前端) → http://localhost:8000 (后端)
```

### 生产环境
```
浏览器 → https://your-domain.com (Nginx)
            ├─→ / → localhost:3000 (前端)
            └─→ /api/ → localhost:8000 (后端)
```

---

## 🚢 完整部署流程（生产环境）

### 1. 准备工作

```bash
# 克隆项目
git clone https://github.com/Stefansong/llm-data-lab.git
cd llm-data-lab
```

### 2. 配置环境变量

```bash
# 使用自动修复脚本
bash deploy.sh fix-env

# 或手动配置
cp backend/.env.example backend/.env
nano backend/.env
# 填入：
# - JWT_SECRET_KEY=<openssl rand -hex 32 生成>
# - OPENAI_API_KEY=sk-your-key
```

### 3. 配置域名和 SSL（如有域名）

```bash
# 替换为你的域名和邮箱
bash deploy.sh domain your-domain.com your-email@example.com
```

### 4. 部署应用

```bash
# 🇨🇳 中国服务器（使用腾讯云镜像 + 域名）
bash deploy.sh start cn prod

# 🌍 国外服务器（使用官方源 + 域名）
bash deploy.sh start prod

# 本地测试（不使用域名）
bash deploy.sh start cn
```

### 5. 验证部署

```bash
# 检查容器状态
docker-compose ps
# 应该显示：
# llm-data-lab-backend   healthy
# llm-data-lab-frontend  running

# 检查前端 API 配置
docker-compose exec frontend env | grep API_BASE_URL

# 测试 API
curl https://your-domain.com/api/health
# 应该返回：{"status":"ok"}

# 浏览器访问
# https://your-domain.com
```

---

## 🔄 更新部署

```bash
# 拉取最新代码
git pull origin main

# 重新部署
bash deploy.sh start cn prod

# 或手动
docker-compose -f docker-compose.yml -f docker-compose.cn.yml -f docker-compose.prod.yml down
docker-compose -f docker-compose.yml -f docker-compose.cn.yml -f docker-compose.prod.yml build
docker-compose -f docker-compose.yml -f docker-compose.cn.yml -f docker-compose.prod.yml up -d
```

---

## 🌍 镜像源配置

### 中国部署（推荐使用镜像加速）

项目已配置腾讯云镜像源，构建速度提升 **70%**：

```bash
# 使用 cn 参数启用镜像加速
bash deploy.sh start cn
```

### 国外部署

```bash
# 不带 cn 参数，使用官方源
bash deploy.sh start
```

### 其他镜像源

如需使用阿里云或其他镜像源，手动指定构建参数：

```bash
docker-compose build \
  --build-arg DEBIAN_MIRROR=mirrors.aliyun.com \
  --build-arg PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/ \
  --build-arg NPM_REGISTRY=https://registry.npmmirror.com/
```

---

## 📖 API 文档

启动服务后，访问：
- **Swagger UI**：http://localhost:8000/docs
- **ReDoc**：http://localhost:8000/redoc
- **OpenAPI JSON**：http://localhost:8000/openapi.json

---

## 🔧 配置说明

### 环境变量优先级

```
1. docker-compose.prod.yml（生产环境覆盖）
2. docker-compose.cn.yml（中国镜像源覆盖）
3. docker-compose.yml（基础配置）
4. backend/.env（本地配置文件）
```

### 部署模式对照

| 模式 | 命令 | API 地址 | 镜像源 |
|-----|------|---------|--------|
| 本地开发 | `docker-compose up` | `http://localhost:8000` | 官方源 |
| 中国测试 | `bash deploy.sh start cn` | `http://backend:8000` | 腾讯云 |
| 生产环境 | `bash deploy.sh start cn prod` | `https://your-domain.com/api` | 腾讯云 |

---

## 💡 最佳实践

### 开发阶段
- ✅ 使用本地开发环境（`npm run dev` + `uvicorn --reload`）
- ✅ 代码提交前先本地测试

### 测试阶段
- ✅ 使用 Docker Compose 部署
- ✅ 使用 `bash deploy.sh start cn` 快速构建

### 生产阶段
- ✅ 配置域名和 SSL 证书
- ✅ 使用 `bash deploy.sh start cn prod` 部署
- ✅ 配置具体的 CORS 域名（不使用 `allow_origins=["*"]`）
- ✅ 定期备份数据库和上传文件
- ✅ 监控服务状态和日志

---

## 🆘 故障排查

### 查看日志

```bash
# 所有服务日志
docker-compose logs -f

# 只看后端
docker-compose logs -f backend

# 只看前端
docker-compose logs -f frontend

# Nginx 日志（如果配置了域名）
sudo tail -f /var/log/nginx/error.log
```

### 诊断工具

```bash
# 全面诊断
bash diagnose.sh

# 这会检查：
# - 配置文件完整性
# - 环境变量设置
# - Docker 容器状态
# - 端口占用情况
# - 服务健康状态
```

### 重置部署

```bash
# 完全清理
docker-compose down -v
docker system prune -f

# 重新部署
bash deploy.sh start cn prod
```

---

## 📚 技术栈

- **后端**：Python 3.10, FastAPI, SQLAlchemy, Pydantic
- **前端**：Next.js 14, React 18, TypeScript, Tailwind CSS
- **数据库**：SQLite (开发), PostgreSQL (生产推荐)
- **部署**：Docker, Docker Compose, Nginx
- **认证**：JWT (HS256)
- **LLM**：OpenAI, Anthropic, DeepSeek, Qwen, SiliconFlow

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！详见 [CONTRIBUTING.md](./CONTRIBUTING.md)

---

## 📄 许可证

MIT License

---

## 📞 支持

- **GitHub Issues**: https://github.com/Stefansong/llm-data-lab/issues
- **文档**: 查看本 README 和项目内的注释

---

**最后更新**：2025-11-05

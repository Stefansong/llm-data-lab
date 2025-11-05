# LLM Data Lab

一个面向科研工作者的数据分析协作平台。用户以自然语言描述任务，系统即可调用多种大语言模型生成 Python 代码，在受控沙箱内执行并输出统计结果、图表与文字总结。

---

## ⚡ 快速开始

### 第一步：克隆项目

```bash
git clone https://github.com/Stefansong/llm-data-lab.git
cd llm-data-lab
```

### 第二步：配置环境变量

```bash
# 自动生成配置文件
bash deploy.sh fix-env

# 编辑配置，填入你的 LLM API Key
nano backend/.env
```

**必须配置**（在 `backend/.env` 中）：
```bash
# JWT 密钥（已自动生成，无需修改）
JWT_SECRET_KEY=<自动生成的64字符随机字符串>

# 至少配置一个 LLM API Key（必需）
OPENAI_API_KEY=sk-your-openai-key-here
# 或
DEEPSEEK_API_KEY=sk-your-deepseek-key-here
# 或
DASHSCOPE_API_KEY=sk-your-qwen-key-here
```

按 `Ctrl+X`，然后 `Y`，再按 `Enter` 保存。

### 第三步：启动服务

```bash
# 🇨🇳 中国服务器（推荐 - 使用腾讯云镜像，构建速度快 70%）
bash deploy.sh start cn

# 🌍 国外服务器
bash deploy.sh start

# 💻 本地开发（不用 Docker）
# 后端：cd backend && pip install -e . && uvicorn backend.main:app --reload
# 前端：cd frontend && npm install && npm run dev
```

### 第四步：访问应用

打开浏览器访问：
- **前端**：http://localhost:3000 或 http://你的服务器IP:3000
- **后端 API 文档**：http://localhost:8000/docs

🎉 **开始使用**：注册账户 → 上传数据 → 自然语言描述任务 → 一键生成并执行代码！

---

## 🌐 配置外网访问

### 使用 IP 地址访问（域名未备案）

如果你的域名未备案或暂时只想用 IP 访问：

```bash
# 在服务器上执行
bash deploy.sh start cn ip
```

脚本会自动：
- ✅ 检测服务器公网 IP
- ✅ 通过环境变量配置前端 API 地址
- ✅ 前端通过 Nginx `/api/` 访问后端（避免 CORS 问题）
- ✅ 支持 HTTP 访问（无需 SSL）

然后在浏览器打开：**http://你的服务器IP**

⚠️ **注意**：只需要基础的 `docker-compose.yml` 和 `docker-compose.cn.yml`，通过环境变量控制 API 地址。

---

## 🌐 配置域名（生产环境）

如果你有域名（例如：`btchuro.com`），可以配置 HTTPS 访问。

### 前置准备

1. ✅ 拥有一个域名
2. ✅ **域名已备案**（如果服务器在中国大陆）
3. ✅ 域名已解析到服务器 IP（添加 A 记录）
4. ✅ 服务器防火墙开放 80 和 443 端口

### 一键配置

```bash
# 在服务器上执行（替换你的域名和邮箱）
bash deploy.sh domain btchuro.com your-email@example.com
```

这会自动：
- ✅ 安装 Nginx
- ✅ 配置反向代理（前端 `/` → `localhost:3000`，后端 `/api/` → `localhost:8000`）
- ✅ 使用 standalone 模式申请免费 SSL 证书（Let's Encrypt）
- ✅ 配置 HTTPS 自动重定向

### 部署到域名

```bash
# 中国服务器 + 生产环境
bash deploy.sh start cn prod

# 国外服务器 + 生产环境
bash deploy.sh start prod
```

### 访问

现在可以通过域名访问：
- **前端**：https://btchuro.com
- **后端 API 文档**：https://btchuro.com/docs

---

## 🔧 常用管理命令

```bash
# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f              # 所有服务
docker-compose logs -f backend      # 只看后端
docker-compose logs -f frontend     # 只看前端

# 重启服务
docker-compose restart

# 停止服务
docker-compose down

# 更新代码并重新部署
git pull origin main
bash deploy.sh start cn prod
```

---

## 🛠️ deploy.sh 使用指南

所有部署操作都通过一个脚本完成：

### 部署应用

```bash
bash deploy.sh start              # 本地/国外，开发测试
bash deploy.sh start cn           # 中国服务器，使用镜像加速
bash deploy.sh start prod         # 生产环境，使用域名访问
bash deploy.sh start cn prod      # 中国 + 生产（推荐）
```

### 配置域名

```bash
bash deploy.sh domain <域名> <邮箱>
# 示例：
bash deploy.sh domain btchuro.com your-email@example.com
```

### 修复配置

```bash
bash deploy.sh fix-env
# 自动生成 JWT_SECRET_KEY
# 验证 .env 文件格式
```

### 查看帮助

```bash
bash deploy.sh help
```

---

## 🐛 常见问题

### 1. 用户注册失败（CORS 错误）

**症状**：
```
Access to fetch at 'http://localhost:8000/auth/register' has been blocked by CORS policy
```

**原因**：前端 API 地址配置错误，或未使用生产配置

**解决方案**：
```bash
# 确保使用 prod 参数部署
bash deploy.sh start cn prod

# 验证 API 地址
docker-compose exec frontend env | grep API_BASE_URL
# 应该显示：NEXT_PUBLIC_API_BASE_URL=https://btchuro.com/api

# 浏览器清除缓存后重试
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
# 自动修复配置
bash deploy.sh fix-env

# 查看详细错误
docker-compose logs backend

# 查看环境变量
cat backend/.env | grep -E "JWT_SECRET_KEY|OPENAI_API_KEY"
```

### 3. Docker 构建速度慢

**症状**：apt-get update 或 pip install 耗时很长（10+ 分钟）

**解决方案**：
```bash
# 🇨🇳 中国服务器：使用 cn 参数启用镜像加速
bash deploy.sh start cn

# 构建时间从 15-20 分钟降至 5-7 分钟（提升 70%）
```

### 4. 域名无法访问

**症状**：浏览器无法打开域名

**检查清单**：
```bash
# 1. 检查域名解析
ping btchuro.com
# 应该显示你的服务器 IP

# 2. 检查 Nginx 状态
sudo systemctl status nginx

# 3. 检查防火墙
sudo ufw status
# 应该允许 80 和 443 端口

# 4. 检查 Docker 容器
docker-compose ps
# 应该显示 backend 和 frontend 都在运行

# 5. 查看 Nginx 日志
sudo tail -f /var/log/nginx/error.log
```

### 5. Git 同步冲突

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

# 注意：这不会影响 backend/.env 文件和 Docker 数据卷
```

---

## 📖 功能说明

### 功能亮点

- **多模型联动**：支持 OpenAI、Anthropic、DeepSeek、Qwen、SiliconFlow 等多个 LLM
- **一键执行**：LLM 生成的 Python 代码自动在沙箱中运行，输出结果和图表
- **数据工作台**：集成数据上传、模型选择、代码编辑、执行结果浏览
- **智能协作**：支持与 LLM 对话，自动生成代码补丁
- **历史留存**：所有任务自动归档，可随时查看代码、结果和附件
- **多用户隔离**：支持用户注册登录，数据完全隔离
- **凭证管理**：API Key 加密存储，多设备自动同步

### 预装的数据分析库

- **数据处理**：pandas, numpy
- **可视化**：matplotlib, seaborn, plotly
- **统计建模**：scipy, statsmodels, lifelines
- **机器学习**：scikit-learn, shap, prophet
- **贝叶斯建模**：pymc, arviz
- **文本处理**：nltk, spacy

---

## 🏗️ 项目结构

```
llm-data-lab/
├── backend/              # FastAPI 后端
│   ├── api/              # REST API 接口
│   ├── llm_adapters/     # LLM 提供商适配器
│   ├── sandbox/          # 代码执行沙箱
│   ├── services/         # 业务逻辑层
│   ├── models/           # 数据库模型
│   └── main.py           # 应用入口
├── frontend/             # Next.js 前端
│   ├── app/              # 页面路由
│   ├── components/       # UI 组件
│   └── lib/              # API 封装
├── prompts/              # LLM 提示词模板
├── deploy.sh             # 统一部署工具
└── README.md             # 本文档
```

---

## 🔒 安全配置

### 生产环境 CORS 配置（推荐）

编辑 `backend/main.py`，将：
```python
allow_origins=["*"],
```

改为具体域名：
```python
allow_origins=[
    "https://btchuro.com",
    "https://www.btchuro.com",
],
```

然后重新部署：
```bash
bash deploy.sh start cn prod
```

### 腾讯云防火墙配置

在腾讯云控制台：
1. 进入**云服务器** → 选择服务器 → **安全组**
2. 添加入站规则：
   - TCP:80（HTTP）
   - TCP:443（HTTPS）

---

## 🌍 镜像源说明

### 为什么要使用镜像源？

在中国服务器上构建 Docker 镜像时：
- ❌ 使用官方源：15-20 分钟
- ✅ 使用腾讯云镜像：5-7 分钟（**提升 70%**）

### 如何使用？

```bash
# 中国服务器：添加 cn 参数
bash deploy.sh start cn

# 国外服务器：不添加 cn 参数
bash deploy.sh start
```

### 支持的镜像源

- **腾讯云**（默认）：`mirrors.cloud.tencent.com`
- **阿里云**：修改 `docker-compose.cn.yml` 中的镜像地址
- **官方源**：不使用 `cn` 参数

---

## 📊 部署架构

### 本地开发
```
浏览器 → http://localhost:3000 (前端)
            ↓
          http://localhost:8000 (后端)
```

### 生产环境（使用域名）
```
浏览器 → https://btchuro.com (Nginx)
            ↓
         ┌──┴──┐
         ↓     ↓
    前端 /    后端 /api/
  (3000)      (8000)
```

**访问示例**：
- `https://btchuro.com/` → 前端主页
- `https://btchuro.com/workspace` → 工作台
- `https://btchuro.com/api/auth/login` → 后端 API
- `https://btchuro.com/docs` → API 文档

---

## 🔄 更新部署

当代码更新后：

```bash
# 拉取最新代码
git pull origin main

# 重新部署
bash deploy.sh start cn prod

# 查看日志
docker-compose logs -f
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

## 🆘 故障排查

### 查看日志

```bash
# 实时查看所有日志
docker-compose logs -f

# 只看后端日志
docker-compose logs -f backend

# 只看前端日志
docker-compose logs -f frontend

# 查看 Nginx 日志（如果配置了域名）
sudo tail -f /var/log/nginx/error.log
```

### SSL 证书申请失败

如果遇到 SSL 验证失败（如 `connect() failed (111)` 错误），脚本已自动使用 standalone 模式：

```bash
# 手动使用 standalone 模式重新申请证书
sudo systemctl stop nginx
sudo certbot certonly --standalone \
    -d btchuro.com \
    -d www.btchuro.com \
    --email your-email@example.com \
    --agree-tos
sudo systemctl start nginx
sudo certbot install --nginx -d btchuro.com
```

### 检查容器状态

```bash
# 查看容器运行状态
docker-compose ps

# 应该显示：
# NAME                   STATUS
# llm-data-lab-backend   Up (healthy)
# llm-data-lab-frontend  Up
```

### 进入容器调试

```bash
# 进入后端容器
docker-compose exec backend bash

# 查看环境变量
env | grep -E "JWT|OPENAI|DATABASE"

# 退出
exit
```

### 完全重置

```bash
# 停止并删除所有容器和数据卷
docker-compose down -v

# 清理 Docker 缓存
docker system prune -f

# 重新部署
bash deploy.sh start cn prod
```

---

## 🎯 完整部署示例（btchuro.com）

假设你要部署到域名 `btchuro.com`，在**腾讯云服务器**上完整流程：

```bash
# 1. 克隆项目
git clone https://github.com/Stefansong/llm-data-lab.git
cd llm-data-lab

# 2. 配置环境变量
bash deploy.sh fix-env
nano backend/.env
# 填入：OPENAI_API_KEY=sk-your-actual-key

# 3. 配置域名和 SSL（替换邮箱）
bash deploy.sh domain btchuro.com your-email@example.com

# 4. 部署应用
bash deploy.sh start cn prod

# 5. 验证
docker-compose ps
docker-compose exec frontend env | grep API_BASE_URL
# 应该显示：NEXT_PUBLIC_API_BASE_URL=https://btchuro.com/api

# 6. 访问
# 浏览器打开：https://btchuro.com
```

完成！现在可以使用了。🎉

---

## 💡 高级配置

### 使用 PostgreSQL（生产推荐）

编辑 `backend/.env`：
```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/llm_data_lab
```

### 自定义镜像源

编辑 `docker-compose.cn.yml`：
```yaml
services:
  backend:
    build:
      args:
        DEBIAN_MIRROR: "mirrors.aliyun.com"
        PIP_INDEX_URL: "https://mirrors.aliyun.com/pypi/simple/"
```

### 配置多个域名

```bash
# 为多个域名申请证书
bash deploy.sh domain btchuro.com your-email@example.com

# 然后手动添加其他域名（使用 standalone 模式）
sudo systemctl stop nginx
sudo certbot certonly --standalone -d api.btchuro.com --email your-email@example.com
sudo systemctl start nginx
sudo certbot install --nginx -d api.btchuro.com
```

---

## 📦 环境变量说明

### 必需配置

| 变量 | 说明 | 示例 |
|-----|------|------|
| `JWT_SECRET_KEY` | JWT 签名密钥（≥32字符） | 自动生成 |
| `OPENAI_API_KEY` | OpenAI API 密钥 | `sk-proj-xxx...` |

### 可选配置

| 变量 | 默认值 | 说明 |
|-----|--------|------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./llm_data_lab.db` | 数据库连接 |
| `ACCESS_TOKEN_EXPIRES_MINUTES` | `43200` (30天) | Token 有效期 |
| `MAX_CODE_EXECUTION_SECONDS` | `60` | 代码执行超时 |
| `MAX_CODE_EXECUTION_MEMORY_MB` | `768` | 代码执行内存限制 |

### 其他 LLM 配置

```env
# Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-xxx

# DeepSeek
DEEPSEEK_API_KEY=sk-xxx
DEEPSEEK_BASE_URL=https://api.deepseek.com

# 通义千问
DASHSCOPE_API_KEY=sk-xxx
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com

# SiliconFlow
SILICONFLOW_API_KEY=sk-xxx
SILICONFLOW_BASE_URL=https://api.siliconflow.cn
```

---

## 🔐 数据安全

### 文件存储

- **上传的数据集**：`./uploaded_datasets/` （Docker 卷持久化）
- **生成的图表**：`./analysis_artifacts/` （Docker 卷持久化）
- **数据库**：`backend-db` Docker 卷

### 备份建议

```bash
# 备份数据库
docker-compose exec backend cp /app/db/llm_data_lab.db /app/db/backup.db

# 导出 Docker 卷
docker run --rm -v llm-data-lab_backend-db:/data -v $(pwd):/backup ubuntu tar czf /backup/backend-db-backup.tar.gz /data

# 备份上传文件和图表
tar czf data-backup.tar.gz uploaded_datasets/ analysis_artifacts/
```

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

开发前请阅读：[CONTRIBUTING.md](./CONTRIBUTING.md)

---

## 📄 许可证

MIT License

---

## 📞 支持

- **GitHub Issues**: https://github.com/Stefansong/llm-data-lab/issues
- **主文档**: 本 README
- **设计文档**: [design.md](./design.md)

---

**最后更新**：2025-11-05  
**项目状态**：✅ 生产就绪

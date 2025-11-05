# 🔧 .env 配置问题修复指南

## 问题描述

后端容器启动失败，报错：
```
ValidationError: 2 validation errors for Settings
openai_base_url
  Extra inputs are not permitted [type=extra_forbidden]
anthropic_default_models
  Extra inputs are not permitted [type=extra_forbidden]
```

**根本原因**：`.env` 文件中包含了一些在 `backend/config.py` 中未定义的配置项。

---

## ✅ 快速修复（在服务器上执行）

### 步骤 1：推送最新代码（在本地 Mac）

```bash
cd /Users/stefan/Desktop/llm_stats_web
git push origin main
```

### 步骤 2：在服务器上拉取并修复

```bash
# SSH 连接到服务器
ssh root@你的腾讯云服务器IP

# 进入项目目录
cd ~/llm-data-lab

# 拉取最新代码（包含修复脚本）
git pull origin main

# 运行自动修复脚本
bash fix-env.sh

# 重新构建并启动
docker-compose down
docker-compose -f docker-compose.yml -f docker-compose.cn.yml build --no-cache
docker-compose -f docker-compose.yml -f docker-compose.cn.yml up -d

# 查看日志
docker-compose logs -f backend
```

---

## 📋 修复脚本做了什么

`fix-env.sh` 会自动：

1. ✅ 备份现有的 `.env` 文件
2. ✅ 提取已配置的 API Keys
3. ✅ 生成新的 JWT_SECRET_KEY（如果需要）
4. ✅ 创建符合 `backend/config.py` 定义的新配置文件
5. ✅ 移除未定义的配置项

**被移除的配置项**：
- ❌ `OPENAI_BASE_URL` （config.py 中未定义）
- ❌ `ANTHROPIC_DEFAULT_MODELS` （config.py 中未定义）

**保留的配置项**：
- ✅ `OPENAI_DEFAULT_MODELS` （config.py 第26行已定义）
- ✅ `DEEPSEEK_DEFAULT_MODELS` （config.py 第32行已定义）
- ✅ `QWEN_DEFAULT_MODELS` （config.py 第38行已定义）
- ✅ `SILICONFLOW_DEFAULT_MODELS` （config.py 第44行已定义）

---

## 🔍 验证修复是否成功

执行以下命令检查：

```bash
# 1. 查看容器状态
docker-compose ps

# 应该看到：
# llm-data-lab-backend   healthy

# 2. 查看后端日志
docker-compose logs backend | tail -20

# 应该看到类似：
# INFO:     Uvicorn running on http://0.0.0.0:8000
# INFO:     Application startup complete

# 3. 测试 API
curl http://localhost:8000/docs
```

---

## 🆘 如果还有问题

### 检查 .env 文件格式

```bash
# 查看 .env 文件内容
cat backend/.env

# 检查关键配置
grep -E "JWT_SECRET_KEY|OPENAI_API_KEY|DEFAULT_MODELS" backend/.env
```

### 手动修复 .env 文件

如果自动脚本失败，可以手动创建：

```bash
cd ~/llm-data-lab

# 创建最小可用配置
cat > backend/.env << 'EOF'
# 安全配置
JWT_SECRET_KEY=$(openssl rand -hex 32)
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRES_MINUTES=43200

# 数据库
DATABASE_URL=sqlite+aiosqlite:///./llm_data_lab.db

# OpenAI（填入你的 API Key）
OPENAI_API_KEY=sk-your-actual-key-here
OPENAI_DEFAULT_MODELS=["gpt-4o","gpt-4o-mini"]

# 执行限制
MAX_CODE_EXECUTION_SECONDS=60
MAX_CODE_EXECUTION_MEMORY_MB=768
EOF

# 生成并更新 JWT_SECRET_KEY
sed -i "s/\$(openssl rand -hex 32)/$(openssl rand -hex 32)/" backend/.env

# 查看生成的配置
cat backend/.env
```

---

## 📖 backend/config.py 中已定义的配置项

以下是所有可以在 `.env` 文件中使用的配置项：

```python
# 应用配置
APP_NAME=LLM Data Lab
ENVIRONMENT=development
FRONTEND_ORIGIN=http://localhost:3000

# 数据库
DATABASE_URL=sqlite+aiosqlite:///./llm_data_lab.db

# OpenAI
OPENAI_API_KEY=
OPENAI_DEFAULT_MODELS=["gpt-4o","gpt-4o-mini"]

# Anthropic
ANTHROPIC_API_KEY=

# DeepSeek
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_DEFAULT_MODELS=["deepseek-chat","deepseek-coder"]

# 通义千问 (Qwen)
DASHSCOPE_API_KEY=
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com
QWEN_DEFAULT_MODELS=["qwen-turbo","qwen-plus","qwen-max"]

# SiliconFlow
SILICONFLOW_API_KEY=
SILICONFLOW_BASE_URL=https://api.siliconflow.cn
SILICONFLOW_DEFAULT_MODELS=["Qwen/Qwen2.5-7B-Instruct"]

# 安全
JWT_SECRET_KEY=
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRES_MINUTES=43200
CREDENTIALS_SECRET_KEY=

# 执行限制
MAX_CODE_EXECUTION_SECONDS=60
MAX_CODE_EXECUTION_MEMORY_MB=768

# 文件上传
UPLOAD_DIR=./uploaded_datasets
ARTIFACTS_DIR=./analysis_artifacts
ALLOWED_UPLOAD_EXTENSIONS=["csv","xlsx","xls"]
```

---

## 🎯 常见问题

### Q: 为什么 OPENAI_BASE_URL 不能用？
**A**: `backend/config.py` 中没有定义这个字段。OpenAI 的 base URL 是硬编码在代码中的。

### Q: 为什么 ANTHROPIC_DEFAULT_MODELS 不能用？
**A**: `backend/config.py` 中只定义了 `anthropic_api_key`，没有定义默认模型列表。

### Q: 如何添加新的配置项？
**A**: 需要在 `backend/config.py` 的 `Settings` 类中添加相应的字段定义，然后重新构建镜像。

---

**最后更新**：2025-11-05  
**问题状态**：✅ 已修复


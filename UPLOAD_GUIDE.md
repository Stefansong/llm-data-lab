# 🚀 GitHub 上传指南

本项目已经准备好上传到 GitHub！以下是详细步骤：

## 📝 准备工作清单

- [x] ✅ 已创建 `.gitignore` 文件
- [x] ✅ 已排除所有敏感数据（数据库、用户数据、环境变量）
- [x] ✅ 已创建 `LICENSE` 文件（MIT 协议）
- [x] ✅ 已创建环境变量示例文件
- [x] ✅ 已创建贡献指南

## 🔧 上传步骤

### 1. 首次提交（本地仓库已初始化）

```bash
# 当前目录已经是 git 仓库，直接添加文件
git add .

# 查看将要提交的文件（确认没有敏感数据）
git status

# 提交到本地仓库
git commit -m "Initial commit: LLM Data Lab - 科研数据分析协作平台"
```

### 2. 在 GitHub 创建仓库

1. 访问 https://github.com/new
2. 填写仓库名称（建议：`llm-data-lab` 或 `llm_stats_web`）
3. 选择 Public 或 Private
4. **不要**勾选 "Add a README file"（我们已经有了）
5. **不要**勾选 "Add .gitignore"（我们已经有了）
6. **不要**选择 License（我们已经有了）
7. 点击 "Create repository"

### 3. 推送到 GitHub

```bash
# 添加远程仓库（替换为你的仓库地址）
git remote add origin https://github.com/你的用户名/仓库名.git

# 重命名主分支为 main（如果需要）
git branch -M main

# 推送到 GitHub
git push -u origin main
```

### 4. 验证上传

访问你的 GitHub 仓库页面，确认：
- ✅ README.md 正常显示
- ✅ LICENSE 文件存在
- ✅ **没有** .db 文件
- ✅ **没有** uploaded_datasets/ 目录
- ✅ **没有** .env 文件
- ✅ **没有** node_modules/ 目录

## 🎯 后续配置建议

### 1. 添加仓库描述
在 GitHub 仓库页面点击 "⚙️ Settings" → "About"，添加：
- **Description**: 科研数据分析协作平台：多模型 LLM + Python 代码生成与执行
- **Topics**: `llm`, `data-analysis`, `python`, `nextjs`, `fastapi`, `research`

### 2. 配置 GitHub Pages（可选）
如果要部署演示站点，可以使用 Vercel 或 GitHub Pages。

### 3. 添加 Badges（可选）
在 README.md 顶部添加状态徽章：
```markdown
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![Next.js](https://img.shields.io/badge/Next.js-14-black)
```

## ⚠️ 重要提醒

### 绝对不要提交的内容：
- ❌ API Keys（OpenAI、Anthropic 等）
- ❌ 数据库文件（.db、.sqlite）
- ❌ 用户上传的真实数据
- ❌ .env 文件
- ❌ node_modules/
- ❌ __pycache__/
- ❌ .next/ 构建文件

### 如果不小心提交了敏感信息：
```bash
# 方法1：删除最后一次提交（如果还没推送）
git reset --soft HEAD~1

# 方法2：从历史中完全删除（已推送的情况）
# 使用 BFG Repo-Cleaner 或 git filter-branch
# 详见：https://docs.github.com/cn/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository
```

## 📚 其他人如何使用你的项目

克隆你的项目后，需要：

```bash
# 1. 克隆仓库
git clone https://github.com/你的用户名/仓库名.git
cd 仓库名

# 2. 后端配置
cd backend
cp .env.example .env
# 编辑 .env，填入 API Keys
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn backend.main:app --reload

# 3. 前端配置（新终端）
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

## 🎉 完成！

现在你的项目已经成功上传到 GitHub，可以分享给全世界了！

---

如有疑问，查看 [CONTRIBUTING.md](CONTRIBUTING.md) 或提交 Issue。

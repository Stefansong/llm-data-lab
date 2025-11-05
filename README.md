# LLM Data Lab

一个面向科研工作者的数据分析协作平台。用户以自然语言描述任务，系统即可调用多种大语言模型生成 Python 代码，在受控沙箱内执行并输出统计结果、图表与文字总结。

## 功能亮点
- **多模型联动**：已适配 OpenAI、Anthropic、DeepSeek、Qwen、SiliconFlow 等 API，便于横向对比不同模型产出的代码与结论。
- **一键执行**：生成的 Python 脚本直接在隔离沙箱中同步运行，产出标准输出、错误日志与图像附件。
- **数据工作台**：集成数据上传、模型选择、代码编辑、执行结果浏览及模型对话协作于一体。
- **历史留存**：所有任务自动归档，可随时查看 prompt、代码、执行日志与生成的附件。
- **多用户隔离**：后端以 `X-User-Id` 头区分用户，上传文件、执行产物、任务记录与会话均按用户单独存储，前端可切换当前用户 ID。
- **凭证集中管理**：每个账户的 API Key、Base URL 与模型设置都会加密保存到后端，可在任意设备登录后自动同步。
- **双模式分析**：可选择“分析策略”（生成详细方案）或“数据分析”（直接执行统计/可视化），提示词会随模式自动调整。
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

## 快速启动

### 🐳 Docker 部署（推荐）

使用 Docker Compose 一键启动所有服务：

```bash
# 1. 配置环境变量
cp backend/.env.example backend/.env
# 编辑 .env 文件，填入 API Keys

# 2. 启动服务
docker-compose up -d

# 3. 访问应用
# 前端：http://localhost:3000
# 后端：http://localhost:8000/docs
```

详细的 Docker 部署指南请查看 [DOCKER_DEPLOY.md](DOCKER_DEPLOY.md)。

### 💻 本地开发部署

#### 后端
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
# 在 .env 中填写所需模型的 API KEY / BASE_URL / DEFAULT_MODELS
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```
- 默认使用 SQLite 数据库存储任务与会话，可在 `.env` 中替换为 PostgreSQL 等。
- 沙箱执行时会在 `uploaded_datasets/user_<id>/` 中保存上传文件，在 `analysis_artifacts/` 中存放运行产生的图表（文件夹名包含用户 ID）。首次启动会自动创建默认用户（ID=1）。
- 调试 REST 接口或编写自定义客户端时，请在请求头中加入 `X-User-Id`（正整数），以便划分数据归属；未指定时默认为 1。
- **升级提示**：若从旧版本升级，请先备份旧的 `llm_data_lab.db`，然后删除该文件或执行“数据库迁移”章节中的 SQL 以补齐 `user_id` 字段。

#### 前端
```bash
cd frontend
npm install
cp .env.example .env.local
# 若后端端口不同，请在 .env.local 中调整 NEXT_PUBLIC_API_BASE_URL
npm run dev
```
访问 <http://localhost:3000>，即可体验：
- **首页**：概览产品价值、操作步骤。
- **数据工作台**：上传数据、生成代码、运行并查看输出，与模型进行对话协作。
- **历史记录**：浏览历史任务详情、下载附件。
- **设置**：管理默认模型、API Key、本地偏好，并可在“个人偏好”中指定当前用户 ID（保存在浏览器），用于区分各自的任务与数据。

## 模型供应商配置
- 各供应商默认凭证仍可在 `backend/.env` 中配置，而用户通过设置页填写的 API Key / Base URL / 默认模型会以加密形式保存在后端数据库，登录后自动加载。
- `.env` 中新增 `CREDENTIALS_SECRET_KEY`（可选）用于加密存储，如未设置则退回 `JWT_SECRET_KEY` 的派生值。
- 如果需要覆盖默认模型列表，可在设置页填写，或者通过 `.env` 的 `*_DEFAULT_MODELS` 调整全局默认。
- 当前适配器均使用同步模式：每次调用会返回完整的模型输出、补丁与 Token 统计信息。

## 用户认证
- 后端使用 JWT（HS256）签发访问令牌，配置项通过 `.env` 中的 `JWT_SECRET_KEY`、`JWT_ALGORITHM`、`ACCESS_TOKEN_EXPIRES_MINUTES` 调整。
- REST 接口需在请求头携带 `Authorization: Bearer <token>`，前端会在登录后自动写入。
- 浏览器访问：打开 `/auth` 页面即可注册或登录；注册成功后立即获取令牌。
- 命令行调试示例：

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"demo1234"}'

# 登录获取 Bearer Token
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"demo1234"}' | jq -r '.access_token')

curl http://localhost:8000/history/tasks \
  -H "Authorization: Bearer ${TOKEN}"
```

## 数据分析能力
后端已预装常用科研分析库：
- 数据处理：`pandas`, `numpy`
- 可视化：`matplotlib`, `seaborn`, `plotly`
- 统计建模：`scipy`, `statsmodels`, `lifelines`
- 机器学习：`scikit-learn`, `shap`, `prophet`
- 贝叶斯与概率建模：`pymc`, `arviz`
- NLP 与文本处理：`nltk`, `spacy`
可根据需求在 `backend/pyproject.toml` 中继续扩展，并重新执行 `pip install -e .`。

## 数据库迁移（从旧版本升级）
如果已有历史数据库，需补充用户信息及外键关系。以下 SQL 适用于 SQLite：

```sql
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY,
  username TEXT NOT NULL UNIQUE,
  email TEXT UNIQUE,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE analysis_tasks ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1;
ALTER TABLE chat_sessions ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1;
ALTER TABLE users ADD COLUMN password_hash TEXT;

UPDATE analysis_tasks SET user_id = 1 WHERE user_id IS NULL;
UPDATE chat_sessions SET user_id = 1 WHERE user_id IS NULL;

INSERT OR IGNORE INTO users (id, username) VALUES (1, 'default');
```

执行完毕后，重新启动后端即可。若希望保持数据库清洁，可在做完备份后直接删除旧的 `llm_data_lab.db`，由应用在首次启动时重新创建。

## 开发常用命令
| 场景 | 命令 |
| ---- | ---- |
| 运行后端（开发模式） | `uvicorn backend.main:app --reload` |
| 运行前端 | `npm run dev` |
| 安装后端依赖 | `pip install -e .` |
| 安装前端依赖 | `npm install` |
| 格式/语法检查 | 依据团队标准自行添加（暂无全局 lint 命令） |

## 设计说明
- **同步执行**：代码执行采用同步 HTTP 接口，结果一次性返回；如需流式或长耗时任务，可在此基础上扩展。
- **沙箱安全**：沙箱会限制执行时间与可用内存，必要时可替换为 Docker 容器或远程执行环境。
- **历史留存**：每次生成/执行均写入数据库表 `analysis_tasks`，便于追溯与比对模型行为。

## 后续改进建议
1. 引入身份认证、团队空间与权限控制。
2. 增加模型流式输出、思考链展示等交互体验。
3. 支持自动生成 Markdown/PDF 报告，并允许一键分享。
4. 构建提示词模板库与版本管理，便于科研复现。

欢迎结合实际场景扩展部署，若有新模型或功能需求，可在 `llm_adapters` 与前端 API 中继续拓展。EOF

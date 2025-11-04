帮我定制一个支持多种大语言模型（LLMs）API调用 + Python代码生成与运行 + 科研数据分析与可视化的网站平台，我们可以设计如下的完整系统架构和功能模块：

⸻

🧠 一、项目定位与核心功能

🌟 目标：

打造一个科研辅助平台，用户通过输入自然语言指令，即可：
	•	调用多个 LLM（如 GPT-4, Claude 等）编写 Python 代码；
	•	实时执行生成的代码；
	•	自动完成数据清洗、统计分析、绘图可视化等科研任务。

🧩 核心功能模块：

功能模块	说明
多模型LLM调用	动态切换 LLM（OpenAI, Anthropic, Google 等）以比较生成效果
指令到代码生成	用户输入科研任务描述，平台生成 Python 代码
在线 Python 执行引擎	安全沙箱环境中执行生成的代码
数据上传与预览	支持上传 CSV/Excel 文件并显示内容
分析与可视化	自动输出图表、表格、描述性统计、回归分析等
会话管理	记录每次分析任务与对应代码、结果
模型表现对比	展示不同 LLM 的代码质量、执行结果对比


⸻

🏗️ 二、技术架构设计（Tech Stack）

1. 前端（Frontend）

技术	用途
Next.js 或 React.js	响应式 SPA 页面
Tailwind CSS	UI 美化，快速构建组件
WebSocket	与后端实时交互，查看代码运行状态
Monaco Editor	集成代码高亮编辑器（类似 VS Code）

2. 后端（Backend）

技术	用途
Python (FastAPI 或 Django)	提供 RESTful API
FastAPI 内置执行	直接在受控沙箱中同步运行代码
Docker 沙箱容器	安全执行 Python 代码，防止恶意指令
SQLite/PostgreSQL	保存用户任务、代码历史等数据

3. LLM 接入层（LLM Layer）

技术	用途
多模型 API 适配器	支持调用 OpenAI, Claude、国内主流模型等 API
Prompt 模板管理	支持不同任务的提示词模板（数据分析、画图等）
Token 用量统计模块	显示用户各模型调用消耗情况

4. 数据处理与可视化库
	•	Pandas：数据处理
	•	Seaborn / Matplotlib / Plotly：绘图
	•	Statsmodels / Scikit-learn：统计建模与机器学习
	•	Jupyter kernel or exec sandbox：运行 Python 代码

⸻

📊 三、功能页面设计（用户视角）

1. 首页（LLM科研助手介绍 + 快速试用）

2. 数据分析工作台
	•	数据上传区（CSV/XLSX）
	•	自然语言输入区（如：“请做一个性别与血压的相关性分析并绘图”）
	•	模型选择：GPT-4、Claude…
	•	Python代码展示区（可手动编辑）
	•	输出区（图表、分析报告、执行日志）

3. 历史记录页面
	•	展示过往分析任务、对应 LLM、代码与结果

4. 设置与API管理
	•	自定义提示词模板
	•	自定义 LLM API Key
	•	设置默认分析风格（可视化样式、语言偏好等）

⸻

🔐 四、安全性与权限管理

机制	描述
Docker 沙箱	限制代码访问权限与执行时间
Token 限流	每个模型设置调用配额防止滥用
文件隔离	用户上传数据不会共享给他人
用户权限系统	登录、注册、团队共享等


⸻

🧪 五、使用场景举例
	•	生信分析：差异表达基因分析 + 火山图自动生成
	•	临床科研：统计描述 + Logistic 回归 + Kaplan-Meier曲线
	•	实验室数据：批量数据清洗、异常值处理、分组对比
	•	自动报告生成：生成带图的 markdown 或 PDF 报告

⸻

🔧 六、部署与运维建议

项目	推荐方案
运行环境	云服务器（如 AWS EC2 + Docker）或 Vercel + Python API 后端
模型调用	OpenAI, Anthropic API Key 用户自己配置
数据存储	本地上传或连接用户的 Google Drive、Dropbox 等
备选方案	JupyterHub 后端 + LLM API 前端封装


⸻

📁 七、文件结构草案（网站源码）

llm-data-lab/
├── frontend/
│   ├── pages/
│   ├── components/
│   └── public/
├── backend/
│   ├── api/
│   ├── llm_adapters/
│   ├── sandbox/  # 安全执行代码
│   └── models/
├── prompts/
│   └── task_templates.yaml
├── notebooks/  # 示例代码/图表
└── README.md

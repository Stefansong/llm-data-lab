# 🚀 最终部署步骤

所有问题已修复！请按以下步骤完成部署。

---

## 📤 第一步：推送到 GitHub（在本地 Mac 执行）

```bash
cd /Users/stefan/Desktop/llm_stats_web
git push origin main
```

如需认证，使用：
- GitHub CLI: `gh auth login`
- 或 Personal Access Token

---

## 🌐 第二步：在腾讯云服务器部署

### A. 首次部署（如果还没克隆代码）

```bash
# 1. SSH 连接
ssh root@你的腾讯云服务器IP

# 2. 安装 Docker（如果还没有）
curl -fsSL https://get.docker.com | bash
apt install docker-compose -y

# 3. 克隆项目
git clone https://github.com/Stefansong/llm-data-lab.git
cd llm-data-lab

# 4. 验证文件
ls -la frontend/lib/       # 应该有 5 个 .ts 文件
ls -la frontend/public/    # 应该有 .gitkeep

# 5. 配置环境变量
cp backend/.env.example backend/.env

# 生成密钥
openssl rand -hex 32

# 编辑配置
nano backend/.env
# 填入：
# JWT_SECRET_KEY=<上面生成的密钥>
# OPENAI_API_KEY=sk-...  (或其他 LLM API Key)

# 6. 一键部署！
bash deploy-server.sh
```

### B. 更新部署（如果已经克隆过）

```bash
# 1. SSH 连接
ssh root@你的腾讯云服务器IP

# 2. 进入项目目录
cd ~/llm-data-lab

# 3. 拉取最新代码
git pull origin main

# 4. 重新部署
bash deploy-server.sh

# 或手动执行：
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

---

## ✅ 验证部署成功

```bash
# 查看服务状态
docker-compose ps

# 应该看到：
# NAME                    STATUS
# llm-data-lab-backend    Up (healthy)
# llm-data-lab-frontend   Up

# 测试访问
curl http://localhost:8000/docs  # 后端
curl http://localhost:3000        # 前端
```

---

## 🌐 访问应用

浏览器打开：
- **前端**：`http://你的服务器IP:3000`
- **后端 API**：`http://你的服务器IP:8000/docs`

---

## 🔒 腾讯云安全组配置

在腾讯云控制台：
1. 云服务器 → 安全组
2. 添加入站规则：
   - 3000/TCP（前端）
   - 8000/TCP（后端）
   - 22/TCP（SSH，应该已有）

---

## 📋 常用命令

```bash
# 查看日志
docker-compose logs -f

# 重启服务
docker-compose restart

# 停止服务
docker-compose down

# 更新代码
git pull origin main
docker-compose up -d --build
```

---

## 🎉 完成！

你的 LLM Data Lab 现在已成功部署到腾讯云！

祝使用愉快！🚀

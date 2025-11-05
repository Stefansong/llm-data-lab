# 🔄 服务器代码同步指南

## 当前情况

- ✅ 本地代码已完成所有修复并提交
- ⏳ 需要推送到 GitHub
- ⏳ 服务器需要强制同步最新代码

---

## 🚀 完整同步步骤

### 第一步：在本地 Mac 推送代码

```bash
cd /Users/stefan/Desktop/llm_stats_web

# 推送到 GitHub
git push origin main

# 如果提示需要认证，输入：
# 用户名: Stefansong
# 密码: <你的 GitHub Personal Access Token>
```

---

### 第二步：在服务器上强制同步

```bash
# SSH 连接到服务器
ssh root@你的服务器IP

# 进入项目目录
cd ~/llm-data-lab

# 查看本地改了什么（可选）
git diff docker-compose.yml

# 🔥 强制同步到 GitHub 最新版本
git fetch origin
git reset --hard origin/main

# 验证同步成功
git log --oneline -5
# 应该显示最新的提交：
# be69d8a fix: 修复生产环境部署的所有配置问题
# de13653 docs: 添加项目全面检查与修复总结
# 302c333 fix: 修复 config.py 和 docker-compose.yml 的配置不一致问题
# ...

# 验证文件存在
ls -la docker-compose.prod.yml
ls -la setup-domain.sh
ls -la fix-env.sh
```

---

### 第三步：部署应用

```bash
cd ~/llm-data-lab

# 方式 1：使用自动化脚本（推荐）
bash deploy-server.sh cn prod

# 方式 2：手动执行
bash fix-env.sh  # 修复 .env 配置
nano backend/.env  # 填入 OpenAI API Key

docker-compose down
docker-compose -f docker-compose.yml -f docker-compose.cn.yml -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.yml -f docker-compose.cn.yml -f docker-compose.prod.yml up -d

# 查看日志
docker-compose logs -f
```

---

### 第四步：验证部署

```bash
# 检查容器状态
docker-compose ps

# 检查前端 API 地址
docker-compose exec frontend env | grep API_BASE_URL
# 应该显示：
# NEXT_PUBLIC_API_BASE_URL=https://btchuro.com/api

# 测试 API
curl https://btchuro.com/api/health
# 应该返回：
# {"status":"ok"}
```

---

## ⚡ 超快速版本（复制整段执行）

### 在本地 Mac：

```bash
cd /Users/stefan/Desktop/llm_stats_web
git push origin main
```

### 在服务器上：

```bash
cd ~/llm-data-lab && \
git fetch origin && \
git reset --hard origin/main && \
bash fix-env.sh && \
bash deploy-server.sh cn prod
```

然后编辑 `backend/.env` 填入 OpenAI API Key。

---

## 🎯 预期结果

执行完上述步骤后：

1. ✅ 服务器代码与 GitHub 完全同步
2. ✅ 前端 API 地址设置为 `https://btchuro.com/api`
3. ✅ 后端 CORS 允许 btchuro.com
4. ✅ 所有配置文件格式正确
5. ✅ 用户可以正常注册和登录

**浏览器访问 https://btchuro.com 应该完全正常！** 🎉

---

## 📋 常见问题

### Q: git reset --hard 会删除我的数据吗？

**A**: 不会！只会重置代码文件，以下内容不受影响：
- ✅ `backend/.env` 文件（已在 .gitignore）
- ✅ 数据库文件（在 Docker 卷中）
- ✅ 上传的数据集（在 Docker 卷中）
- ✅ 生成的图表（在 Docker 卷中）

### Q: 如果 git push 需要配置 SSH 密钥怎么办？

**A**: 参考以下快速配置：

```bash
# 在本地 Mac 生成 SSH 密钥
ssh-keygen -t ed25519 -C "your-email@example.com"

# 查看公钥
cat ~/.ssh/id_ed25519.pub

# 复制公钥，添加到 GitHub：
# GitHub.com → Settings → SSH and GPG keys → New SSH key

# 修改远程仓库地址
cd /Users/stefan/Desktop/llm_stats_web
git remote set-url origin git@github.com:Stefansong/llm-data-lab.git

# 推送
git push origin main
```

---

**现在执行第一步：在本地推送代码！** 🚀


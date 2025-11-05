#!/bin/bash
# LLM Data Lab - 云服务器部署脚本
# 使用方法：bash deploy-server.sh

set -e  # 遇到错误立即退出

echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║           LLM Data Lab - 云服务器部署脚本                            ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"
echo ""

# 1. 检查是否在正确的目录
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ 错误：请在项目根目录运行此脚本"
    exit 1
fi

echo "✅ 当前目录：$(pwd)"
echo ""

# 2. 拉取最新代码
echo "📥 步骤 1/8: 拉取最新代码..."
git pull origin main
echo ""

# 3. 验证关键文件
echo "🔍 步骤 2/8: 验证文件完整性..."
if [ ! -d "frontend/lib" ]; then
    echo "❌ 错误：frontend/lib/ 目录不存在！"
    echo "   请确保已执行 git pull"
    exit 1
fi

echo "检查关键文件："
ls -l frontend/lib/api.ts && echo "  ✅ api.ts"
ls -l frontend/lib/authToken.ts && echo "  ✅ authToken.ts"
ls -l frontend/lib/i18n.ts && echo "  ✅ i18n.ts"
ls -l frontend/lib/userProfile.ts && echo "  ✅ userProfile.ts"
echo ""

# 4. 检查环境变量配置
echo "⚙️  步骤 3/8: 检查环境变量..."
if [ ! -f "backend/.env" ]; then
    echo "⚠️  警告：backend/.env 不存在"
    echo "   正在创建示例文件..."
    cp backend/.env.example backend/.env
    echo "   ✅ 已创建 backend/.env，请编辑此文件填入 API Keys！"
    echo ""
    echo "   重要：必须配置以下内容："
    echo "   - JWT_SECRET_KEY（至少32字符）"
    echo "   - 至少一个 LLM API Key"
    echo ""
    read -p "   按回车继续（确保已配置好 .env 文件）..."
else
    echo "  ✅ backend/.env 已存在"
fi
echo ""

# 5. 停止现有服务
echo "🛑 步骤 4/8: 停止现有服务..."
docker-compose down -v
echo ""

# 6. 清理 Docker 缓存
echo "🧹 步骤 5/8: 清理 Docker 缓存..."
docker system prune -f
echo ""

# 7. 构建镜像
echo "🔨 步骤 6/8: 构建 Docker 镜像（使用国内镜像源，预计 5-7 分钟）..."
echo "   后端构建中（这可能需要几分钟）..."
docker-compose build --no-cache backend
echo "   ✅ 后端构建完成"
echo ""
echo "   前端构建中..."
docker-compose build --no-cache frontend
echo "   ✅ 前端构建完成"
echo ""

# 8. 启动服务
echo "🚀 步骤 7/8: 启动所有服务..."
docker-compose up -d
echo ""

# 9. 等待服务启动
echo "⏳ 步骤 8/8: 等待服务启动（10秒）..."
sleep 10
echo ""

# 10. 检查服务状态
echo "📊 服务状态："
docker-compose ps
echo ""

# 11. 健康检查
echo "🏥 健康检查："
if curl -sf http://localhost:8000/docs > /dev/null; then
    echo "  ✅ 后端运行正常：http://localhost:8000/docs"
else
    echo "  ❌ 后端未响应，请查看日志：docker-compose logs backend"
fi

if curl -sf http://localhost:3000 > /dev/null; then
    echo "  ✅ 前端运行正常：http://localhost:3000"
else
    echo "  ❌ 前端未响应，请查看日志：docker-compose logs frontend"
fi
echo ""

echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║                   🎉 部署完成！                                       ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "🌐 访问地址："
echo "   前端：http://$(hostname -I | awk '{print $1}'):3000"
echo "   后端：http://$(hostname -I | awk '{print $1}'):8000/docs"
echo ""
echo "📋 常用命令："
echo "   查看日志：docker-compose logs -f"
echo "   重启服务：docker-compose restart"
echo "   停止服务：docker-compose down"
echo ""
echo "✨ 祝使用愉快！"


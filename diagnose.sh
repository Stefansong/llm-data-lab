#!/bin/bash
# LLM Data Lab - 诊断脚本
# 使用方法：bash diagnose.sh

echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║           LLM Data Lab - 故障诊断工具                                ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"
echo ""

# 1. 检查项目目录
echo "📁 检查 1/8: 项目目录"
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ 错误：请在项目根目录运行此脚本"
    exit 1
fi
echo "✅ 当前目录：$(pwd)"
echo ""

# 2. 检查关键文件
echo "📋 检查 2/8: 关键文件"
FILES_TO_CHECK=(
    "docker-compose.yml"
    "docker-compose.cn.yml"
    "backend/Dockerfile"
    "frontend/Dockerfile"
    "backend/.env"
)

for file in "${FILES_TO_CHECK[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file 不存在！"
    fi
done
echo ""

# 3. 检查 .env 配置
echo "⚙️  检查 3/8: 环境变量配置"
if [ -f "backend/.env" ]; then
    echo "  ✅ backend/.env 存在"
    
    # 检查 JWT_SECRET_KEY
    JWT_KEY=$(grep "^JWT_SECRET_KEY=" backend/.env | cut -d'=' -f2 | tr -d '"' | tr -d "'")
    JWT_LENGTH=${#JWT_KEY}
    
    if [ -z "$JWT_KEY" ]; then
        echo "  ❌ JWT_SECRET_KEY 未设置"
    elif [ $JWT_LENGTH -lt 32 ]; then
        echo "  ❌ JWT_SECRET_KEY 长度不足（当前 $JWT_LENGTH 字符，需要至少 32 字符）"
        echo "     当前值：$JWT_KEY"
    else
        echo "  ✅ JWT_SECRET_KEY 已配置（长度：$JWT_LENGTH 字符）"
    fi
    
    # 检查 LLM API Keys
    echo ""
    echo "  LLM API Keys 配置："
    API_KEYS=(
        "OPENAI_API_KEY"
        "ANTHROPIC_API_KEY"
        "DEEPSEEK_API_KEY"
        "DASHSCOPE_API_KEY"
        "SILICONFLOW_API_KEY"
    )
    
    HAS_API_KEY=false
    for key in "${API_KEYS[@]}"; do
        VALUE=$(grep "^${key}=" backend/.env | cut -d'=' -f2 | tr -d '"' | tr -d "'")
        if [ -n "$VALUE" ] && [ "$VALUE" != "" ]; then
            echo "    ✅ $key 已配置"
            HAS_API_KEY=true
        fi
    done
    
    if [ "$HAS_API_KEY" = false ]; then
        echo "    ⚠️  警告：未检测到任何 LLM API Key"
    fi
else
    echo "  ❌ backend/.env 不存在"
    echo "     请运行：cp backend/.env.example backend/.env"
fi
echo ""

# 4. 检查 Docker 状态
echo "🐳 检查 4/8: Docker 服务"
if command -v docker &> /dev/null; then
    echo "  ✅ Docker 已安装：$(docker --version)"
    
    if docker ps &> /dev/null; then
        echo "  ✅ Docker 服务运行中"
    else
        echo "  ❌ Docker 服务未运行或权限不足"
        echo "     请运行：sudo systemctl start docker"
    fi
else
    echo "  ❌ Docker 未安装"
fi
echo ""

# 5. 检查容器状态
echo "📦 检查 5/8: 容器状态"
if docker-compose ps &> /dev/null; then
    docker-compose ps
else
    echo "  ⚠️  无法获取容器状态（可能尚未启动）"
fi
echo ""

# 6. 检查后端日志
echo "📝 检查 6/8: 后端日志（最后 30 行）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if docker-compose ps | grep -q "llm-data-lab-backend"; then
    docker-compose logs --tail=30 backend
else
    echo "  ⚠️  后端容器未运行"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 7. 检查端口占用
echo "🔌 检查 7/8: 端口占用"
PORTS=(8000 3000)
for port in "${PORTS[@]}"; do
    if command -v lsof &> /dev/null; then
        if lsof -i :$port &> /dev/null; then
            echo "  ⚠️  端口 $port 已被占用："
            lsof -i :$port
        else
            echo "  ✅ 端口 $port 可用"
        fi
    elif command -v netstat &> /dev/null; then
        if netstat -tuln | grep -q ":$port "; then
            echo "  ⚠️  端口 $port 已被占用"
        else
            echo "  ✅ 端口 $port 可用"
        fi
    else
        echo "  ⚠️  无法检查端口（缺少 lsof 或 netstat）"
    fi
done
echo ""

# 8. 健康检查
echo "🏥 检查 8/8: 服务健康状态"
if curl -sf http://localhost:8000/docs &> /dev/null; then
    echo "  ✅ 后端健康：http://localhost:8000/docs"
else
    echo "  ❌ 后端不健康"
    echo ""
    echo "  正在尝试访问健康检查端点..."
    HEALTH_OUTPUT=$(curl -s http://localhost:8000/docs 2>&1 || echo "连接失败")
    echo "  响应：$HEALTH_OUTPUT"
fi

if curl -sf http://localhost:3000 &> /dev/null; then
    echo "  ✅ 前端健康：http://localhost:3000"
else
    echo "  ❌ 前端不健康"
fi
echo ""

# 诊断总结
echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║                   诊断完成                                            ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"
echo ""

echo "💡 常见问题解决方案："
echo ""
echo "1️⃣ 如果 JWT_SECRET_KEY 长度不足："
echo "   sed -i \"s/JWT_SECRET_KEY=.*/JWT_SECRET_KEY=\$(openssl rand -hex 32)/\" backend/.env"
echo ""
echo "2️⃣ 如果缺少 LLM API Key："
echo "   nano backend/.env  # 填入至少一个 API Key"
echo ""
echo "3️⃣ 如果后端日志显示错误，查看完整日志："
echo "   docker-compose logs backend | less"
echo ""
echo "4️⃣ 重新部署："
echo "   bash deploy-server.sh cn  # 中国服务器"
echo "   bash deploy-server.sh     # 国外服务器"
echo ""
echo "5️⃣ 完全清理重建："
echo "   docker-compose down -v"
echo "   docker system prune -f"
echo "   bash deploy-server.sh cn"
echo ""


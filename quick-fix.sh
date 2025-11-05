#!/bin/bash
# LLM Data Lab - 快速修复脚本
# 使用方法：bash quick-fix.sh

set -e

echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║           LLM Data Lab - 快速修复工具                                ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"
echo ""

# 1. 检查是否在项目根目录
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ 错误：请在项目根目录运行此脚本"
    exit 1
fi

echo "✅ 当前目录：$(pwd)"
echo ""

# 2. 检查并创建 .env 文件
echo "🔧 步骤 1/5: 检查环境变量文件..."
if [ ! -f "backend/.env" ]; then
    echo "  ⚠️  backend/.env 不存在，从示例文件创建..."
    if [ -f "backend/.env.example" ]; then
        cp backend/.env.example backend/.env
        echo "  ✅ 已创建 backend/.env"
    else
        echo "  ❌ backend/.env.example 不存在，创建基础配置..."
        cat > backend/.env << 'EOF'
# 安全配置
JWT_SECRET_KEY=change-this-to-a-32-character-secret-key-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRES_MINUTES=43200

# 数据库
DATABASE_URL=sqlite:///./db/llm_data_lab.db

# LLM API Keys（至少配置一个）
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
DEEPSEEK_API_KEY=
DASHSCOPE_API_KEY=
SILICONFLOW_API_KEY=

# 执行限制
MAX_CODE_EXECUTION_SECONDS=60
MAX_CODE_EXECUTION_MEMORY_MB=512
EOF
        echo "  ✅ 已创建基础配置文件"
    fi
fi
echo ""

# 3. 修复 JWT_SECRET_KEY
echo "🔑 步骤 2/5: 检查并修复 JWT_SECRET_KEY..."
JWT_KEY=$(grep "^JWT_SECRET_KEY=" backend/.env | cut -d'=' -f2 | tr -d '"' | tr -d "'" || echo "")
JWT_LENGTH=${#JWT_KEY}

if [ -z "$JWT_KEY" ] || [ $JWT_LENGTH -lt 32 ]; then
    echo "  ⚠️  JWT_SECRET_KEY 长度不足（当前 $JWT_LENGTH 字符），正在生成新密钥..."
    
    # 生成新密钥
    if command -v openssl &> /dev/null; then
        NEW_SECRET=$(openssl rand -hex 32)
    else
        # 如果没有 openssl，使用 Python
        NEW_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || echo "")
        
        if [ -z "$NEW_SECRET" ]; then
            # 如果 Python 也失败，使用 /dev/urandom
            NEW_SECRET=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 64 | head -n 1)
        fi
    fi
    
    # 更新 .env 文件
    if grep -q "^JWT_SECRET_KEY=" backend/.env; then
        sed -i.bak "s|^JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$NEW_SECRET|" backend/.env
    else
        echo "JWT_SECRET_KEY=$NEW_SECRET" >> backend/.env
    fi
    
    echo "  ✅ 已生成新的 JWT_SECRET_KEY（长度：${#NEW_SECRET} 字符）"
    echo "  📝 密钥：$NEW_SECRET"
    echo "  ⚠️  请妥善保存此密钥！"
else
    echo "  ✅ JWT_SECRET_KEY 配置正确（长度：$JWT_LENGTH 字符）"
fi
echo ""

# 4. 检查 LLM API Keys
echo "🤖 步骤 3/5: 检查 LLM API Keys..."
API_KEYS=(
    "OPENAI_API_KEY"
    "ANTHROPIC_API_KEY"
    "DEEPSEEK_API_KEY"
    "DASHSCOPE_API_KEY"
    "SILICONFLOW_API_KEY"
)

HAS_API_KEY=false
for key in "${API_KEYS[@]}"; do
    VALUE=$(grep "^${key}=" backend/.env | cut -d'=' -f2 | tr -d '"' | tr -d "'" || echo "")
    if [ -n "$VALUE" ] && [ "$VALUE" != "" ]; then
        echo "  ✅ $key 已配置"
        HAS_API_KEY=true
    fi
done

if [ "$HAS_API_KEY" = false ]; then
    echo ""
    echo "  ⚠️  警告：未检测到任何 LLM API Key！"
    echo ""
    echo "  请编辑 backend/.env 文件，至少配置一个 API Key："
    echo "  nano backend/.env"
    echo ""
    echo "  支持的 LLM 提供商："
    echo "    - OpenAI (https://platform.openai.com/api-keys)"
    echo "    - Anthropic Claude (https://console.anthropic.com/)"
    echo "    - DeepSeek (https://platform.deepseek.com/)"
    echo "    - 通义千问 (https://dashscope.console.aliyun.com/)"
    echo "    - SiliconFlow (https://siliconflow.cn/)"
    echo ""
    read -p "  按回车继续（确保稍后配置 API Key）..." || true
fi
echo ""

# 5. 停止现有服务
echo "🛑 步骤 4/5: 停止现有服务..."
if docker-compose ps 2>/dev/null | grep -q "llm-data-lab"; then
    docker-compose down -v
    echo "  ✅ 已停止现有服务"
else
    echo "  ℹ️  没有运行中的服务"
fi
echo ""

# 6. 清理 Docker 缓存
echo "🧹 步骤 5/5: 清理 Docker 缓存..."
docker system prune -f &> /dev/null || true
echo "  ✅ 已清理 Docker 缓存"
echo ""

# 完成
echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║                   修复完成！                                          ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"
echo ""

# 显示配置摘要
echo "📋 当前配置摘要："
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
cat backend/.env | grep -E "^(JWT_SECRET_KEY|OPENAI_API_KEY|ANTHROPIC_API_KEY|DEEPSEEK_API_KEY|DASHSCOPE_API_KEY|SILICONFLOW_API_KEY)=" | sed 's/=\(.\{10\}\).*/=\1.../' || true
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "🚀 下一步："
echo ""
echo "1️⃣ 如果还未配置 LLM API Key，请编辑配置文件："
echo "   nano backend/.env"
echo ""
echo "2️⃣ 部署服务："
echo "   🇨🇳 中国服务器：bash deploy-server.sh cn"
echo "   🌍 国外服务器：bash deploy-server.sh"
echo ""
echo "3️⃣ 查看日志："
echo "   docker-compose logs -f"
echo ""


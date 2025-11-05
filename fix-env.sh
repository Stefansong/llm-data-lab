#!/bin/bash
# LLM Data Lab - 自动修复 .env 配置文件
# 使用方法：bash fix-env.sh

set -e

echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║           LLM Data Lab - .env 配置修复工具                           ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"
echo ""

# 检查是否在项目根目录
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ 错误：请在项目根目录运行此脚本"
    exit 1
fi

echo "✅ 当前目录：$(pwd)"
echo ""

# 备份现有 .env 文件
if [ -f "backend/.env" ]; then
    echo "📦 备份现有配置..."
    cp backend/.env backend/.env.backup.$(date +%Y%m%d_%H%M%S)
    echo "  ✅ 已备份到 backend/.env.backup.$(date +%Y%m%d_%H%M%S)"
    
    # 提取现有的关键配置
    OLD_JWT_SECRET=$(grep "^JWT_SECRET_KEY=" backend/.env | cut -d'=' -f2 || echo "")
    OLD_OPENAI_KEY=$(grep "^OPENAI_API_KEY=" backend/.env | cut -d'=' -f2 || echo "")
    OLD_ANTHROPIC_KEY=$(grep "^ANTHROPIC_API_KEY=" backend/.env | cut -d'=' -f2 || echo "")
    OLD_DEEPSEEK_KEY=$(grep "^DEEPSEEK_API_KEY=" backend/.env | cut -d'=' -f2 || echo "")
    OLD_DASHSCOPE_KEY=$(grep "^DASHSCOPE_API_KEY=" backend/.env | cut -d'=' -f2 || echo "")
    OLD_SILICONFLOW_KEY=$(grep "^SILICONFLOW_API_KEY=" backend/.env | cut -d'=' -f2 || echo "")
else
    echo "⚠️  未找到现有 .env 文件，将创建新文件"
    OLD_JWT_SECRET=""
    OLD_OPENAI_KEY=""
    OLD_ANTHROPIC_KEY=""
    OLD_DEEPSEEK_KEY=""
    OLD_DASHSCOPE_KEY=""
    OLD_SILICONFLOW_KEY=""
fi
echo ""

# 如果没有 JWT_SECRET_KEY，生成一个
if [ -z "$OLD_JWT_SECRET" ] || [ "$OLD_JWT_SECRET" == "change-this-to-a-32-character-secret-key-in-production" ]; then
    echo "🔑 生成新的 JWT_SECRET_KEY..."
    if command -v openssl &> /dev/null; then
        NEW_JWT_SECRET=$(openssl rand -hex 32)
    else
        NEW_JWT_SECRET=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 64 | head -n 1)
    fi
    echo "  ✅ 已生成：${NEW_JWT_SECRET:0:20}..."
    JWT_SECRET=$NEW_JWT_SECRET
else
    echo "✅ 保留现有 JWT_SECRET_KEY"
    JWT_SECRET=$OLD_JWT_SECRET
fi
echo ""

# 创建新的 .env 文件
echo "📝 创建新的 .env 文件..."
cat > backend/.env << EOF
# ============================================
# LLM Data Lab - 环境变量配置
# ============================================
# 自动生成于：$(date +"%Y-%m-%d %H:%M:%S")

# ============================================
# 安全配置（必需）
# ============================================
JWT_SECRET_KEY=$JWT_SECRET
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRES_MINUTES=43200

# ============================================
# 数据库配置
# ============================================
DATABASE_URL=sqlite+aiosqlite:///./llm_data_lab.db

# ============================================
# LLM API 配置（至少配置一个）
# ============================================

# OpenAI
OPENAI_API_KEY=${OLD_OPENAI_KEY}
OPENAI_DEFAULT_MODELS=["gpt-4o","gpt-4o-mini","gpt-4-turbo"]

# Anthropic Claude
ANTHROPIC_API_KEY=${OLD_ANTHROPIC_KEY}

# DeepSeek
DEEPSEEK_API_KEY=${OLD_DEEPSEEK_KEY}
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_DEFAULT_MODELS=["deepseek-chat","deepseek-coder"]

# 通义千问 (Qwen)
DASHSCOPE_API_KEY=${OLD_DASHSCOPE_KEY}
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com
QWEN_DEFAULT_MODELS=["qwen-turbo","qwen-plus","qwen-max"]

# SiliconFlow
SILICONFLOW_API_KEY=${OLD_SILICONFLOW_KEY}
SILICONFLOW_BASE_URL=https://api.siliconflow.cn
SILICONFLOW_DEFAULT_MODELS=["Qwen/Qwen2.5-7B-Instruct","deepseek-ai/DeepSeek-V2.5"]

# ============================================
# 代码执行限制
# ============================================
MAX_CODE_EXECUTION_SECONDS=60
MAX_CODE_EXECUTION_MEMORY_MB=768
EOF

echo "  ✅ 新配置文件已创建"
echo ""

# 显示配置摘要
echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║                   配置摘要                                            ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "JWT_SECRET_KEY: ${JWT_SECRET:0:20}... (${#JWT_SECRET} 字符)"
echo ""
echo "已配置的 LLM API Keys:"
[ -n "$OLD_OPENAI_KEY" ] && echo "  ✅ OpenAI" || echo "  ⚠️  OpenAI (未配置)"
[ -n "$OLD_ANTHROPIC_KEY" ] && echo "  ✅ Anthropic" || echo "  ⚠️  Anthropic (未配置)"
[ -n "$OLD_DEEPSEEK_KEY" ] && echo "  ✅ DeepSeek" || echo "  ⚠️  DeepSeek (未配置)"
[ -n "$OLD_DASHSCOPE_KEY" ] && echo "  ✅ 通义千问" || echo "  ⚠️  通义千问 (未配置)"
[ -n "$OLD_SILICONFLOW_KEY" ] && echo "  ✅ SiliconFlow" || echo "  ⚠️  SiliconFlow (未配置)"
echo ""

# 检查是否至少有一个 API Key
if [ -z "$OLD_OPENAI_KEY" ] && [ -z "$OLD_ANTHROPIC_KEY" ] && [ -z "$OLD_DEEPSEEK_KEY" ] && [ -z "$OLD_DASHSCOPE_KEY" ] && [ -z "$OLD_SILICONFLOW_KEY" ]; then
    echo "⚠️  警告：未检测到任何 LLM API Key！"
    echo ""
    echo "请编辑 backend/.env 文件，至少配置一个 API Key："
    echo "  nano backend/.env"
    echo ""
    read -p "按回车继续..."
fi

echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║                   修复完成！                                          ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"
echo ""

echo "🚀 下一步："
echo ""
echo "1️⃣ 如果需要修改 API Key，请编辑配置文件："
echo "   nano backend/.env"
echo ""
echo "2️⃣ 重新构建并启动服务："
echo "   docker-compose down"
echo "   docker-compose -f docker-compose.yml -f docker-compose.cn.yml build --no-cache"
echo "   docker-compose -f docker-compose.yml -f docker-compose.cn.yml up -d"
echo ""
echo "3️⃣ 查看日志："
echo "   docker-compose logs -f backend"
echo ""


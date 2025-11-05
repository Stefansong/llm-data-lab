#!/bin/bash
# LLM Data Lab - 统一部署工具
# 使用方法：
#   bash deploy.sh start [cn] [prod]          # 部署应用
#   bash deploy.sh domain <domain> <email>    # 配置域名和 SSL
#   bash deploy.sh fix-env                    # 修复环境变量
#   bash deploy.sh help                       # 显示帮助

set -e

COMMAND=$1

# ============================================
# 显示帮助信息
# ============================================
show_help() {
    cat << 'EOF'
╔════════════════════════════════════════════════════════════════════════╗
║           LLM Data Lab - 统一部署工具                                ║
╚════════════════════════════════════════════════════════════════════════╝

📦 部署应用：
  bash deploy.sh start              # 本地/国外服务器部署
  bash deploy.sh start cn           # 中国服务器（使用镜像加速）
  bash deploy.sh start cn ip        # 使用 IP 访问（域名未备案时）
  bash deploy.sh start prod         # 生产环境（使用域名）
  bash deploy.sh start cn prod      # 中国 + 生产环境（推荐）

🌐 配置域名：
  bash deploy.sh domain btchuro.com your-email@example.com
  # 自动配置 Nginx + 使用 standalone 模式申请 SSL 证书

🔧 修复配置：
  bash deploy.sh fix-env
  # 自动修复 .env 文件（生成密钥、验证格式）

📖 显示帮助：
  bash deploy.sh help

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 常用部署场景：

1. 本地测试：
   bash deploy.sh start

2. 腾讯云部署（域名未备案，使用 IP 访问）：
   bash deploy.sh fix-env
   bash deploy.sh start cn ip

3. 腾讯云部署（域名已备案）：
   bash deploy.sh fix-env
   bash deploy.sh domain btchuro.com your-email@example.com
   bash deploy.sh start cn prod

4. 更新部署：
   git pull origin main
   bash deploy.sh start cn prod  # 或 cn ip

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF
}

# ============================================
# 修复环境变量
# ============================================
fix_env() {
    echo "╔════════════════════════════════════════════════════════════════════════╗"
    echo "║           修复环境变量配置                                            ║"
    echo "╚════════════════════════════════════════════════════════════════════════╝"
    echo ""
    
    if [ ! -f "backend/.env" ]; then
        echo "📝 创建 .env 文件..."
        if [ -f "backend/.env.example" ]; then
            cp backend/.env.example backend/.env
        fi
    fi
    
    # 检查并生成 JWT_SECRET_KEY
    JWT_KEY=$(grep "^JWT_SECRET_KEY=" backend/.env 2>/dev/null | cut -d'=' -f2 | tr -d '"' | tr -d "'" || echo "")
    JWT_LENGTH=${#JWT_KEY}
    
    if [ -z "$JWT_KEY" ] || [ $JWT_LENGTH -lt 32 ]; then
        echo "🔑 生成 JWT_SECRET_KEY..."
        NEW_SECRET=$(openssl rand -hex 32 2>/dev/null || cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 64 | head -n 1)
        
        if grep -q "^JWT_SECRET_KEY=" backend/.env 2>/dev/null; then
            sed -i.bak "s|^JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$NEW_SECRET|" backend/.env
        else
            echo "JWT_SECRET_KEY=$NEW_SECRET" >> backend/.env
        fi
        
        echo "  ✅ 已生成 JWT_SECRET_KEY（${#NEW_SECRET} 字符）"
    else
        echo "✅ JWT_SECRET_KEY 已配置（${JWT_LENGTH} 字符）"
    fi
    
    echo ""
    echo "⚠️  请确保至少配置一个 LLM API Key："
    echo "  nano backend/.env"
    echo ""
}

# ============================================
# 配置域名和 SSL
# ============================================
setup_domain() {
    DOMAIN=$2
    EMAIL=$3
    
    if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
        echo "❌ 错误：请提供域名和邮箱"
        echo "用法: bash deploy.sh domain <domain> <email>"
        echo "示例: bash deploy.sh domain btchuro.com your-email@example.com"
        exit 1
    fi
    
    echo "╔════════════════════════════════════════════════════════════════════════╗"
    echo "║           配置域名和 SSL                                              ║"
    echo "╚════════════════════════════════════════════════════════════════════════╝"
    echo ""
    echo "域名: $DOMAIN"
    echo "邮箱: $EMAIL"
    echo ""
    
    # 安装依赖
    echo "📦 安装 Nginx 和 Certbot..."
    if ! command -v nginx &> /dev/null; then
        sudo apt update
        sudo apt install -y nginx
    fi
    
    if ! command -v certbot &> /dev/null; then
        sudo apt install -y certbot python3-certbot-nginx
    fi
    echo "  ✅ 依赖已安装"
    echo ""
    
    # 创建 Nginx 配置
    echo "⚙️  创建 Nginx 配置..."
    sudo tee /etc/nginx/sites-available/llm-data-lab > /dev/null << EOF
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
    
    client_max_body_size 100M;
    
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
    }
    
    location /api/ {
        rewrite ^/api/(.*) /\$1 break;
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    location /docs {
        proxy_pass http://localhost:8000/docs;
        proxy_set_header Host \$host;
    }
    
    location /openapi.json {
        proxy_pass http://localhost:8000/openapi.json;
        proxy_set_header Host \$host;
    }
}
EOF
    
    # 启用配置
    sudo ln -sf /etc/nginx/sites-available/llm-data-lab /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default
    
    # 测试并重启
    if sudo nginx -t; then
        sudo systemctl restart nginx
        echo "  ✅ Nginx 配置成功"
    else
        echo "  ❌ Nginx 配置有错误"
        exit 1
    fi
    echo ""
    
    # 申请 SSL 证书（使用 standalone 模式）
    echo "🔒 申请 SSL 证书（standalone 模式）..."
    echo "  ⏸️  临时停止 Nginx..."
    sudo systemctl stop nginx
    
    if sudo certbot certonly --standalone \
        -d $DOMAIN \
        -d www.$DOMAIN \
        --non-interactive \
        --agree-tos \
        --email "$EMAIL"; then
        echo "  ✅ SSL 证书申请成功"
        
        # 启动 Nginx
        echo "  ▶️  启动 Nginx..."
        sudo systemctl start nginx
        
        # 配置 Nginx SSL
        echo "  ⚙️  配置 Nginx SSL..."
        if sudo certbot install --nginx -d $DOMAIN --non-interactive; then
            echo "  ✅ SSL 配置完成，已启用 HTTPS 重定向"
        else
            echo "  ⚠️  自动配置失败，需要手动配置 SSL"
            echo "  证书位置："
            echo "    /etc/letsencrypt/live/$DOMAIN/fullchain.pem"
            echo "    /etc/letsencrypt/live/$DOMAIN/privkey.pem"
        fi
    else
        echo "  ⚠️  SSL 证书申请失败，但 HTTP 访问可用"
        echo "  ▶️  启动 Nginx..."
        sudo systemctl start nginx
    fi
    
    echo ""
    echo "╔════════════════════════════════════════════════════════════════════════╗"
    echo "║                   🎉 域名配置完成！                                   ║"
    echo "╚════════════════════════════════════════════════════════════════════════╝"
    echo ""
    echo "🌐 访问地址："
    echo "   https://$DOMAIN"
    echo "   https://$DOMAIN/docs"
    echo ""
}

# ============================================
# 部署应用
# ============================================
deploy_start() {
    shift  # 移除 'start' 参数
    
    echo "╔════════════════════════════════════════════════════════════════════════╗"
    echo "║           LLM Data Lab - 应用部署                                    ║"
    echo "╚════════════════════════════════════════════════════════════════════════╝"
    echo ""
    
    # 检查目录
    if [ ! -f "docker-compose.yml" ]; then
        echo "❌ 错误：请在项目根目录运行此脚本"
        exit 1
    fi
    
    echo "✅ 当前目录：$(pwd)"
    echo ""
    
    # 解析参数
    COMPOSE_FILES="-f docker-compose.yml"
    USE_CN_MIRROR=false
    USE_PROD_CONFIG=false
    USE_IP_ACCESS=false
    
    for arg in "$@"; do
        if [ "$arg" == "cn" ]; then
            USE_CN_MIRROR=true
        elif [ "$arg" == "prod" ]; then
            USE_PROD_CONFIG=true
        elif [ "$arg" == "ip" ]; then
            USE_IP_ACCESS=true
        fi
    done
    
    # 配置文件
    if [ "$USE_CN_MIRROR" == "true" ]; then
        echo "🇨🇳 使用腾讯云镜像源加速"
        COMPOSE_FILES="$COMPOSE_FILES -f docker-compose.cn.yml"
    fi
    
    if [ "$USE_PROD_CONFIG" == "true" ]; then
        echo "🌐 生产环境模式（域名访问）"
        if [ -f "docker-compose.prod.yml" ]; then
            COMPOSE_FILES="$COMPOSE_FILES -f docker-compose.prod.yml"
        fi
    fi
    
    if [ "$USE_IP_ACCESS" == "true" ]; then
        echo "🌐 IP 访问模式"
        
        # 获取服务器公网 IP
        SERVER_IP=$(curl -s ifconfig.me || curl -s icanhazip.com || hostname -I | awk '{print $1}')
        
        if [ -z "$SERVER_IP" ]; then
            echo "  ⚠️  无法自动获取公网 IP，请手动设置 NEXT_PUBLIC_API_BASE_URL"
            export NEXT_PUBLIC_API_BASE_URL="http://YOUR_SERVER_IP/api"
        else
            echo "  📍 检测到服务器 IP：$SERVER_IP"
            # 设置环境变量（前端通过 Nginx /api/ 访问后端）
            export NEXT_PUBLIC_API_BASE_URL="http://$SERVER_IP/api"
            echo "  ✅ 已设置 API 地址：$NEXT_PUBLIC_API_BASE_URL"
        fi
    fi
    
    echo "  配置：$COMPOSE_FILES"
    echo ""
    
    # 拉取代码
    if [ -d ".git" ]; then
        echo "📥 拉取最新代码..."
        git pull origin main || echo "⚠️  代码拉取失败，继续使用本地版本"
        echo ""
    fi
    
    # 检查 .env
    echo "⚙️  检查环境变量..."
    if [ ! -f "backend/.env" ]; then
        echo "  ⚠️  backend/.env 不存在"
        echo "  运行: bash deploy.sh fix-env"
        exit 1
    fi
    
    JWT_KEY=$(grep "^JWT_SECRET_KEY=" backend/.env | cut -d'=' -f2 | tr -d '"' | tr -d "'" || echo "")
    if [ ${#JWT_KEY} -lt 32 ]; then
        echo "  ⚠️  JWT_SECRET_KEY 长度不足"
        echo "  运行: bash deploy.sh fix-env"
        exit 1
    fi
    echo "  ✅ 配置检查通过"
    echo ""
    
    # 停止旧服务
    echo "🛑 停止现有服务..."
    docker-compose $COMPOSE_FILES down -v || true
    echo ""
    
    # 清理缓存
    echo "🧹 清理 Docker 缓存..."
    docker system prune -f
    echo ""
    
    # 构建镜像
    echo "🔨 构建 Docker 镜像（预计 5-7 分钟）..."
    docker-compose $COMPOSE_FILES build --no-cache
    echo ""
    
    # 启动服务
    echo "🚀 启动服务..."
    docker-compose $COMPOSE_FILES up -d
    echo ""
    
    # 等待启动
    echo "⏳ 等待服务启动（10秒）..."
    sleep 10
    echo ""
    
    # 检查状态
    echo "📊 服务状态："
    docker-compose $COMPOSE_FILES ps
    echo ""
    
    # 健康检查
    echo "🏥 健康检查："
    if curl -sf http://localhost:8000/docs > /dev/null; then
        echo "  ✅ 后端运行正常"
    else
        echo "  ❌ 后端未响应，查看日志：docker-compose logs backend"
    fi
    
    if curl -sf http://localhost:3000 > /dev/null; then
        echo "  ✅ 前端运行正常"
    else
        echo "  ❌ 前端未响应，查看日志：docker-compose logs frontend"
    fi
    echo ""
    
    echo "╔════════════════════════════════════════════════════════════════════════╗"
    echo "║                   🎉 部署完成！                                       ║"
    echo "╚════════════════════════════════════════════════════════════════════════╝"
    echo ""
    
    if [ "$USE_PROD_CONFIG" == "true" ]; then
        echo "🌐 访问地址："
        echo "   前端：https://btchuro.com"
        echo "   后端：https://btchuro.com/docs"
    elif [ "$USE_IP_ACCESS" == "true" ]; then
        echo "🌐 访问地址（通过 Nginx）："
        SERVER_IP=$(curl -s ifconfig.me || curl -s icanhazip.com || hostname -I | awk '{print $1}')
        echo "   前端：http://$SERVER_IP"
        echo "   后端：http://$SERVER_IP/api/docs"
        echo ""
        echo "✅ 已配置 Nginx 反向代理，前端通过 /api/ 访问后端，避免 CORS 问题"
    else
        echo "🌐 访问地址："
        SERVER_IP=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "localhost")
        echo "   前端：http://$SERVER_IP:3000"
        echo "   后端：http://$SERVER_IP:8000/docs"
    fi
    echo ""
    echo "📋 常用命令："
    echo "   查看日志：docker-compose logs -f"
    echo "   重启服务：docker-compose restart"
    echo "   停止服务：docker-compose down"
    echo ""
}

# ============================================
# 主逻辑
# ============================================
case "$COMMAND" in
    start)
        deploy_start "$@"
        ;;
    domain)
        setup_domain "$@"
        ;;
    fix-env)
        fix_env
        ;;
    help|--help|-h|"")
        show_help
        ;;
    *)
        echo "❌ 未知命令: $COMMAND"
        echo ""
        show_help
        exit 1
        ;;
esac


#!/bin/bash
# LLM Data Lab - 域名配置自动化脚本
# 使用方法：bash setup-domain.sh btchuro.com your-email@example.com

set -e

DOMAIN=$1
EMAIL=$2

if [ -z "$DOMAIN" ]; then
    echo "❌ 错误：请提供域名"
    echo "用法: bash setup-domain.sh your-domain.com your-email@example.com"
    exit 1
fi

if [ -z "$EMAIL" ]; then
    echo "❌ 错误：请提供邮箱地址（用于 SSL 证书通知）"
    echo "用法: bash setup-domain.sh your-domain.com your-email@example.com"
    exit 1
fi

echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║           LLM Data Lab - 域名配置工具                                ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "域名: $DOMAIN"
echo "邮箱: $EMAIL"
echo ""

# 1. 检查域名解析
echo "🔍 步骤 1/6: 检查域名解析..."
if ping -c 1 $DOMAIN &> /dev/null; then
    RESOLVED_IP=$(ping -c 1 $DOMAIN | grep -oP '\(\K[^\)]+' | head -1)
    echo "  ✅ 域名已解析到: $RESOLVED_IP"
else
    echo "  ⚠️  警告：无法 ping 通域名，请确保 DNS 已生效"
    read -p "  是否继续？(y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi
echo ""

# 2. 安装依赖
echo "📦 步骤 2/6: 安装 Nginx 和 Certbot..."
if command -v nginx &> /dev/null; then
    echo "  ✅ Nginx 已安装"
else
    echo "  正在安装 Nginx..."
    sudo apt update
    sudo apt install -y nginx
fi

if command -v certbot &> /dev/null; then
    echo "  ✅ Certbot 已安装"
else
    echo "  正在安装 Certbot..."
    sudo apt install -y certbot python3-certbot-nginx
fi
echo ""

# 3. 创建 Nginx 配置
echo "⚙️  步骤 3/6: 创建 Nginx 配置..."
sudo tee /etc/nginx/sites-available/llm-data-lab > /dev/null << EOF
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
    
    client_max_body_size 100M;
    
    # 前端
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
    
    # 后端 API
    location /api/ {
        rewrite ^/api/(.*) /\$1 break;
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    # API 文档
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

echo "  ✅ Nginx 配置已创建"
echo ""

# 4. 启用配置
echo "🔗 步骤 4/6: 启用 Nginx 配置..."
sudo ln -sf /etc/nginx/sites-available/llm-data-lab /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
echo "  ✅ 配置已启用"
echo ""

# 5. 测试并重启 Nginx
echo "🧪 步骤 5/6: 测试 Nginx 配置..."
if sudo nginx -t; then
    echo "  ✅ Nginx 配置测试通过"
    sudo systemctl restart nginx
    echo "  ✅ Nginx 已重启"
else
    echo "  ❌ Nginx 配置有错误，请检查"
    exit 1
fi
echo ""

# 6. 申请 SSL 证书
echo "🔒 步骤 6/6: 申请免费 SSL 证书..."
if sudo certbot --nginx \
    -d $DOMAIN \
    -d www.$DOMAIN \
    --non-interactive \
    --agree-tos \
    --email "$EMAIL" \
    --redirect; then
    echo "  ✅ SSL 证书申请成功"
else
    echo "  ⚠️  SSL 证书申请失败，但 HTTP 访问仍然可用"
    echo "  请检查域名是否已正确解析，然后重新运行："
    echo "  sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN"
fi
echo ""

# 完成
echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║                   🎉 域名配置完成！                                   ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "🌐 访问地址："
echo "   主页:      https://$DOMAIN"
echo "   API 文档:  https://$DOMAIN/docs"
echo ""
echo "📋 下一步："
echo "1. 更新 docker-compose.yml 中的 NEXT_PUBLIC_API_BASE_URL"
echo "   export NEXT_PUBLIC_API_BASE_URL=https://$DOMAIN/api"
echo ""
echo "2. 重新构建并启动前端容器："
echo "   cd ~/llm-data-lab"
echo "   docker-compose down"
echo "   docker-compose -f docker-compose.yml -f docker-compose.cn.yml -f docker-compose.prod.yml build frontend"
echo "   docker-compose -f docker-compose.yml -f docker-compose.cn.yml -f docker-compose.prod.yml up -d"
echo ""
echo "🔄 SSL 证书会在 90 天后自动续期"
echo ""


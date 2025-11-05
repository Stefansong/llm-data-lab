# 后端 Dockerfile - Python + FastAPI + 科学计算库
FROM python:3.10-slim

# 🌍 构建参数：允许自定义镜像源（支持国内外部署）
ARG DEBIAN_MIRROR=""
ARG PIP_INDEX_URL="https://pypi.org/simple"
ARG PIP_TRUSTED_HOST=""

# 设置工作目录  
WORKDIR /app

# 🔥 可选：替换 Debian 镜像源（仅在提供 DEBIAN_MIRROR 时）
RUN if [ -n "$DEBIAN_MIRROR" ]; then \
        sed -i "s|deb.debian.org|$DEBIAN_MIRROR|g" /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
        sed -i "s|deb.debian.org|$DEBIAN_MIRROR|g" /etc/apt/sources.list; \
    fi

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# 🔥 配置 pip 镜像源（支持自定义）
RUN pip config set global.index-url "$PIP_INDEX_URL" && \
    pip config set global.timeout 300 && \
    if [ -n "$PIP_TRUSTED_HOST" ]; then \
        pip config set install.trusted-host "$PIP_TRUSTED_HOST"; \
    fi

# 复制整个项目到 backend 目录
COPY . /app/backend/

# 安装依赖（增加超时和重试次数）
RUN cd /app/backend && \
    pip install --no-cache-dir \
    --default-timeout=300 \
    --retries=10 \
    -e .

# 设置工作目录为 app（backend 的父目录）
WORKDIR /app

# 创建必要的目录
RUN mkdir -p /app/uploaded_datasets /app/analysis_artifacts

# 设置环境变量
ENV PYTHONPATH=/app
ENV UPLOAD_DIR=/app/uploaded_datasets
ENV ARTIFACTS_DIR=/app/analysis_artifacts

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/docs || exit 1

# 启动命令（使用 python -m 方式）
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

# 后端 Dockerfile - Python + FastAPI + 科学计算库
FROM python:3.10-slim

# 设置工作目录  
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# 复制整个项目到 backend 目录
COPY . /app/backend/

# 安装依赖
RUN cd /app/backend && pip install --no-cache-dir -e .

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

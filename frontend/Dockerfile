# 前端 Dockerfile - Next.js 多阶段构建
# 阶段 1: 依赖安装
FROM node:18-alpine AS deps

WORKDIR /app

# 复制依赖文件
COPY package.json package-lock.json ./

# 🔥 配置 npm 使用腾讯云镜像源（加速下载）
RUN npm config set registry https://mirrors.cloud.tencent.com/npm/

# 安装依赖
RUN npm ci

# 阶段 2: 构建应用
FROM node:18-alpine AS builder

WORKDIR /app

# 从 deps 阶段复制 node_modules
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# 设置环境变量
ENV NEXT_TELEMETRY_DISABLED 1

# 确保 public 目录存在（即使为空）
RUN mkdir -p ./public

# 构建应用
RUN npm run build

# 阶段 3: 生产运行
FROM node:18-alpine AS runner

WORKDIR /app

ENV NODE_ENV production
ENV NEXT_TELEMETRY_DISABLED 1

# 创建非 root 用户
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# 复制构建结果
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# 复制 public 目录（builder 阶段已确保存在）
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs

EXPOSE 3000

ENV PORT 3000
ENV HOSTNAME "0.0.0.0"

# 启动命令
CMD ["node", "server.js"]

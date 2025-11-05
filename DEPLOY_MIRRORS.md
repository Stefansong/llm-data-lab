# 🌍 镜像源配置指南

本项目支持灵活的镜像源配置，可在**中国大陆**和**海外**服务器上快速部署。

---

## 📦 架构设计

项目使用 **Docker 构建参数（ARG）** 实现镜像源可配置化：

### 后端 (Python)
- `DEBIAN_MIRROR`: Debian 系统包镜像源
- `PIP_INDEX_URL`: Python 包镜像源
- `PIP_TRUSTED_HOST`: pip 信任的主机

### 前端 (Node.js)
- `NPM_REGISTRY`: npm 包镜像源

---

## 🚀 快速部署

### 方式 1：使用部署脚本（推荐）

#### 🇨🇳 中国服务器部署
```bash
bash deploy-server.sh cn
```

#### 🌍 国外服务器部署
```bash
bash deploy-server.sh
```

---

### 方式 2：使用 Docker Compose 配置文件

#### 🇨🇳 中国服务器部署
```bash
# 使用 docker-compose.cn.yml 覆盖配置
docker-compose -f docker-compose.yml -f docker-compose.cn.yml build
docker-compose -f docker-compose.yml -f docker-compose.cn.yml up -d
```

#### 🌍 国外服务器部署
```bash
# 使用默认配置（官方源）
docker-compose build
docker-compose up -d
```

---

### 方式 3：手动指定构建参数

#### 🇨🇳 中国服务器 - 腾讯云镜像
```bash
docker-compose build \
  --build-arg DEBIAN_MIRROR=mirrors.cloud.tencent.com \
  --build-arg PIP_INDEX_URL=https://mirrors.cloud.tencent.com/pypi/simple/ \
  --build-arg PIP_TRUSTED_HOST=mirrors.cloud.tencent.com \
  --build-arg NPM_REGISTRY=https://mirrors.cloud.tencent.com/npm/
```

#### 🇨🇳 中国服务器 - 阿里云镜像
```bash
docker-compose build \
  --build-arg DEBIAN_MIRROR=mirrors.aliyun.com \
  --build-arg PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/ \
  --build-arg PIP_TRUSTED_HOST=mirrors.aliyun.com \
  --build-arg NPM_REGISTRY=https://registry.npmmirror.com/
```

#### 🇨🇳 中国服务器 - 清华大学镜像
```bash
docker-compose build \
  --build-arg DEBIAN_MIRROR=mirrors.tuna.tsinghua.edu.cn \
  --build-arg PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple/ \
  --build-arg PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn \
  --build-arg NPM_REGISTRY=https://mirrors.tuna.tsinghua.edu.cn/npm/
```

#### 🌍 国外服务器 - 官方源
```bash
docker-compose build
# 或显式指定
docker-compose build \
  --build-arg DEBIAN_MIRROR="" \
  --build-arg PIP_INDEX_URL=https://pypi.org/simple \
  --build-arg NPM_REGISTRY=https://registry.npmjs.org/
```

---

## ⏱️ 预期构建时间对比

| 部署地区 | 镜像源 | 后端构建 | 前端构建 | 总时间 |
|---------|--------|---------|---------|--------|
| 🇨🇳 中国（腾讯云） | 腾讯云镜像 | 3-4 分钟 ⚡ | 2-3 分钟 ⚡ | **5-7 分钟** |
| 🇨🇳 中国（阿里云） | 阿里云镜像 | 3-4 分钟 ⚡ | 2-3 分钟 ⚡ | **5-7 分钟** |
| 🇨🇳 中国 | 官方源 | 10-15 分钟 🐌 | 5-8 分钟 🐌 | **15-23 分钟** |
| 🌍 美国/欧洲 | 官方源 | 5-7 分钟 | 3-4 分钟 | **8-11 分钟** |
| 🇭🇰 香港/新加坡 | 官方源 | 4-6 分钟 | 2-3 分钟 | **6-9 分钟** |

---

## 🔧 自定义镜像源

如果你有**私有镜像仓库**或想使用其他镜像源，可以：

### 1. 创建自定义 Compose 覆盖文件
```yaml
# docker-compose.custom.yml
services:
  backend:
    build:
      args:
        DEBIAN_MIRROR: "your-debian-mirror.com"
        PIP_INDEX_URL: "https://your-pypi-mirror.com/simple/"
        PIP_TRUSTED_HOST: "your-pypi-mirror.com"
  
  frontend:
    build:
      args:
        NPM_REGISTRY: "https://your-npm-mirror.com/"
```

### 2. 使用自定义配置部署
```bash
docker-compose -f docker-compose.yml -f docker-compose.custom.yml up -d
```

---

## 🐛 故障排除

### 问题 1：构建超时
**症状**：`ReadTimeoutError: HTTPSConnectionPool... Read timed out.`

**解决方案**：
```bash
# 1. 中国服务器：使用国内镜像
bash deploy-server.sh cn

# 2. 增加 Docker 构建超时
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1
docker-compose build --no-cache
```

### 问题 2：DNS 解析失败
**症状**：`Could not resolve host: deb.debian.org`

**解决方案**：
```bash
# 配置 DNS
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf
echo "nameserver 114.114.114.114" | sudo tee -a /etc/resolv.conf
```

### 问题 3：镜像源不可用
**症状**：`404 Not Found` 或 `Failed to fetch`

**解决方案**：
```bash
# 切换到其他镜像源
docker-compose build \
  --build-arg DEBIAN_MIRROR=mirrors.aliyun.com \
  --build-arg PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
```

---

## 📚 配置文件说明

### `docker-compose.yml`
- **默认配置**：使用官方源
- **适用于**：国外服务器、或不需要加速的环境

### `docker-compose.cn.yml`
- **覆盖配置**：使用腾讯云镜像
- **适用于**：中国大陆服务器
- **使用方法**：`docker-compose -f docker-compose.yml -f docker-compose.cn.yml up -d`

### `deploy-server.sh`
- **智能部署脚本**：自动选择配置
- **参数**：
  - 无参数：使用官方源（国外）
  - `cn` 参数：使用腾讯云镜像（中国）

---

## 🌐 支持的镜像源列表

### 中国大陆镜像源

| 提供商 | Debian | PyPI | npm |
|--------|--------|------|-----|
| 腾讯云 | `mirrors.cloud.tencent.com` | `https://mirrors.cloud.tencent.com/pypi/simple/` | `https://mirrors.cloud.tencent.com/npm/` |
| 阿里云 | `mirrors.aliyun.com` | `https://mirrors.aliyun.com/pypi/simple/` | `https://registry.npmmirror.com/` |
| 清华大学 | `mirrors.tuna.tsinghua.edu.cn` | `https://pypi.tuna.tsinghua.edu.cn/simple/` | `https://mirrors.tuna.tsinghua.edu.cn/npm/` |
| 中国科技大学 | `mirrors.ustc.edu.cn` | `https://pypi.mirrors.ustc.edu.cn/simple/` | `https://npmreg.proxy.ustclug.org/` |
| 华为云 | `mirrors.huaweicloud.com` | `https://mirrors.huaweicloud.com/repository/pypi/simple/` | `https://mirrors.huaweicloud.com/repository/npm/` |

### 官方源

| 服务 | 地址 |
|-----|------|
| Debian | `deb.debian.org` |
| PyPI | `https://pypi.org/simple` |
| npm | `https://registry.npmjs.org/` |

---

## 💡 最佳实践

1. **本地开发**：使用官方源（避免镜像源同步延迟导致版本不一致）
2. **中国生产环境**：使用 `deploy-server.sh cn` 或 `docker-compose.cn.yml`
3. **国外生产环境**：使用 `deploy-server.sh` 或默认 `docker-compose.yml`
4. **CI/CD 流水线**：根据 Runner 地区动态选择配置文件

---

## 🔒 安全建议

- ✅ **生产环境**：使用企业级镜像仓库（如阿里云容器镜像服务）
- ✅ **敏感项目**：自建私有镜像仓库
- ⚠️ **公共镜像**：定期检查镜像源可用性和安全性
- ⚠️ **HTTPS**：确保所有镜像源使用 HTTPS（避免中间人攻击）

---

## 📖 相关文档

- [Docker 部署完整指南](./DOCKER_DEPLOY.md)
- [GitHub 上传指南](./UPLOAD_GUIDE.md)
- [部署检查清单](./DEPLOY_CHECKLIST.md)

---

**最后更新**：2025-11-05  
**维护者**：LLM Data Lab Team


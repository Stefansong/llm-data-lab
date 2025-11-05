import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import inspect, select, text
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .api import auth, chat, execution, files, history, llm, provider_settings
from .config import get_settings
from .database import database, engine, metadata
from . import models  # noqa: F401 ensure models are registered
from .models.user import users

# 配置日志系统
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 🔒 配置速率限制
limiter = Limiter(key_func=get_remote_address, default_limits=["1000/hour"])


def ensure_user_table_schema() -> None:
    with engine.begin() as connection:
        inspector = inspect(connection)
        table_names = inspector.get_table_names()
        if "users" not in table_names:
            return
        column_names = {column["name"] for column in inspector.get_columns("users")}
        if "password_hash" not in column_names:
            logger.info("Adding password_hash column to users table")
            connection.execute(text("ALTER TABLE users ADD COLUMN password_hash TEXT"))

settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0")

# 🔒 配置速率限制器
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 自定义速率限制错误响应
@app.exception_handler(RateLimitExceeded)
async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    logger.warning(f"Rate limit exceeded for {request.client.host}")
    return JSONResponse(
        status_code=429,
        content={
            "detail": "请求过于频繁，请稍后再试",
            "error": "rate_limit_exceeded"
        }
    )

# 🔒 安全的 CORS 配置
# 根据环境变量决定允许的来源
allowed_origins = settings.allowed_origins or [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

logger.info(f"CORS allowed origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,  # 🔒 不允许凭证传递（使用 Authorization header 代替）
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
    max_age=3600,
)


@app.on_event("startup")
async def startup_event() -> None:
    """应用启动事件：初始化数据库和验证安全配置"""
    logger.info("Starting LLM Data Lab application...")

    # 🔒 安全检查：验证 JWT 密钥
    if settings.jwt_secret_key == "change-me-change-me-change-me-change":
        logger.error("CRITICAL: JWT_SECRET_KEY is using default value!")
        raise RuntimeError(
            "❌ 安全错误：必须设置 JWT_SECRET_KEY 环境变量！\n"
            "运行: bash deploy.sh fix-env"
        )

    if len(settings.jwt_secret_key) < 64:
        logger.warning(f"JWT_SECRET_KEY length is {len(settings.jwt_secret_key)}, recommended >= 64")
    else:
        logger.info(f"JWT_SECRET_KEY configured (length: {len(settings.jwt_secret_key)})")

    # 日志关键配置
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Token expires: {settings.access_token_expires_minutes} minutes")
    logger.info(f"Database: {settings.database_url.split('://')[0]}")

    # 初始化数据库
    ensure_user_table_schema()
    metadata.create_all(bind=engine)
    if not database.is_connected:
        await database.connect()
        logger.info("Database connected")

    # 创建默认用户（如果不存在）
    default_user = await database.fetch_one(select(users.c.id).where(users.c.id == 1))
    if default_user is None:
        await database.execute(
            users.insert().values(id=1, username="default", email=None, password_hash=None)
        )
        logger.info("Created default user")

    logger.info("Application started successfully!")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    if database.is_connected:
        await database.disconnect()


app.include_router(auth.router)
app.include_router(llm.router)
app.include_router(provider_settings.router)
app.include_router(execution.router)
app.include_router(files.router)
app.include_router(history.router)
app.include_router(chat.router)


@app.get("/health", tags=["meta"])
async def health_check() -> dict:
    return {"status": "ok"}

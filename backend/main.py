from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, select, text

from .api import auth, chat, execution, files, history, llm, provider_settings
from .config import get_settings
from .database import database, engine, metadata
from . import models  # noqa: F401 ensure models are registered
from .models.user import users


def ensure_user_table_schema() -> None:
    with engine.begin() as connection:
        inspector = inspect(connection)
        table_names = inspector.get_table_names()
        if "users" not in table_names:
            return
        column_names = {column["name"] for column in inspector.get_columns("users")}
        if "password_hash" not in column_names:
            connection.execute(text("ALTER TABLE users ADD COLUMN password_hash TEXT"))

settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 🌐 允许所有来源（生产环境建议配置具体域名）
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event() -> None:
    ensure_user_table_schema()
    metadata.create_all(bind=engine)
    if not database.is_connected:
        await database.connect()
    default_user = await database.fetch_one(select(users.c.id).where(users.c.id == 1))
    if default_user is None:
        await database.execute(
            users.insert().values(id=1, username="default", email=None, password_hash=None)
        )


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

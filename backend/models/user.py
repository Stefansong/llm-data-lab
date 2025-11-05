from sqlalchemy import Column, DateTime, Integer, String, Table, text

from ..database import metadata

users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("username", String(150), nullable=False, unique=True, index=True),  # 🔍 索引：用户名查询
    Column("email", String(255), nullable=True, unique=True, index=True),  # 🔍 索引：邮箱查询
    Column("password_hash", String(255), nullable=True),
    Column("created_at", DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"), index=True),  # 🔍 索引：按注册时间排序
)

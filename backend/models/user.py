from sqlalchemy import Column, DateTime, Integer, String, Table, text

from ..database import metadata

users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("username", String(150), nullable=False, unique=True),
    Column("email", String(255), nullable=True, unique=True),
    Column("password_hash", String(255), nullable=True),
    Column("created_at", DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
)

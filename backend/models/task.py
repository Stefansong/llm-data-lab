from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table, Text, func, text

from ..database import metadata


def utcnow() -> datetime:
    return datetime.utcnow()


analysis_tasks = Table(
    "analysis_tasks",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("user_id", Integer, ForeignKey("users.id"), nullable=False, server_default=text("1")),
    Column("title", String(255), nullable=False),
    Column("prompt", Text, nullable=False),
    Column("model", String(64), nullable=False),
    Column("generated_code", Text, nullable=True),
    Column("execution_stdout", Text, nullable=True),
    Column("execution_stderr", Text, nullable=True),
    Column("status", String(32), nullable=False, server_default=text("'queued'")),
    Column("created_at", DateTime, nullable=False, server_default=func.now()),
    Column(
        "updated_at",
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=utcnow,
        server_onupdate=func.now(),
    ),
    Column("dataset_filename", String(255), nullable=True),
    Column("summary", Text, nullable=True),
)

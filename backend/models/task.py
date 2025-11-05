from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Table, Text, func, text

from ..database import metadata


def utcnow() -> datetime:
    return datetime.utcnow()


analysis_tasks = Table(
    "analysis_tasks",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("user_id", Integer, ForeignKey("users.id"), nullable=False, server_default=text("1"), index=True),  # 🔍 索引：用户任务查询
    Column("title", String(255), nullable=False),
    Column("prompt", Text, nullable=False),
    Column("model", String(64), nullable=False),
    Column("generated_code", Text, nullable=True),
    Column("execution_stdout", Text, nullable=True),
    Column("execution_stderr", Text, nullable=True),
    Column("status", String(32), nullable=False, server_default=text("'queued'"), index=True),  # 🔍 索引：状态过滤
    Column("created_at", DateTime, nullable=False, server_default=func.now(), index=True),  # 🔍 索引：时间排序
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
    # 🔍 复合索引：用户+状态（常见查询组合）
    Index("idx_tasks_user_status", "user_id", "status"),
    # 🔍 复合索引：用户+创建时间（分页查询）
    Index("idx_tasks_user_created", "user_id", "created_at"),
)

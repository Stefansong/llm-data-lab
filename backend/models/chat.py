from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    text,
)

from ..database import metadata


chat_sessions = Table(
    "chat_sessions",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id"), nullable=False, server_default=text("1"), index=True),  # 🔍 索引：用户会话查询
    Column("task_id", Integer, ForeignKey("analysis_tasks.id"), nullable=True, index=True),  # 🔍 索引：任务会话查询
    Column("model", String(64), nullable=False),
    Column("title", String(255), nullable=True),
    Column("created_at", DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"), index=True),  # 🔍 索引：时间排序
    Column(
        "updated_at",
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=datetime.utcnow,
        index=True,  # 🔍 索引：最近更新排序
    ),
    # 🔍 复合索引：用户+更新时间（获取用户最近会话）
    Index("idx_sessions_user_updated", "user_id", "updated_at"),
)


chat_messages = Table(
    "chat_messages",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("session_id", Integer, ForeignKey("chat_sessions.id"), nullable=False, index=True),  # 🔍 索引：会话消息查询
    Column("role", String(16), nullable=False),
    Column("content", Text, nullable=False),
    Column("metadata", Text, nullable=True),
    Column("created_at", DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"), index=True),  # 🔍 索引：时间排序
    # 🔍 复合索引：会话+创建时间（按时间获取会话消息）
    Index("idx_messages_session_created", "session_id", "created_at"),
)

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table, Text, UniqueConstraint, func, text

from ..database import metadata

provider_credentials = Table(
    "provider_credentials",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id"), nullable=False),
    Column("provider_id", String(64), nullable=False),
    Column("api_key_encrypted", Text, nullable=True),
    Column("base_url", String(255), nullable=True),
    Column("default_models", Text, nullable=True),
    Column("created_at", DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    Column(
        "updated_at",
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=datetime.utcnow,
    ),
    UniqueConstraint("user_id", "provider_id", name="uq_provider_credentials_user_provider"),
)

import json
from datetime import datetime
from typing import Optional

from databases import Database
from sqlalchemy import insert, select, update

from ..models.chat import chat_messages, chat_sessions
from ..models.task import analysis_tasks
from ..schemas import ChatMessagePayload


async def ensure_session(
    db: Database,
    *,
    session_id: Optional[int],
    task_id: Optional[int],
    model: str,
    user_id: int,
) -> int:
    if session_id:
        result = await db.fetch_one(
            select(chat_sessions.c.id)
            .where(chat_sessions.c.id == session_id)
            .where(chat_sessions.c.user_id == user_id)
        )
        if result:
            await db.execute(
                update(chat_sessions)
                .where(chat_sessions.c.id == session_id)
                .values(updated_at=datetime.utcnow())
            )
            return session_id

    query = (
        insert(chat_sessions)
        .values(
            task_id=task_id,
            model=model,
            user_id=user_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        .returning(chat_sessions.c.id)
    )
    new_id = await db.execute(query)
    return new_id


async def append_message(
    db: Database,
    *,
    session_id: int,
    role: str,
    content: str,
    metadata: Optional[dict] = None,
) -> None:
    await db.execute(
        insert(chat_messages).values(
            session_id=session_id,
            role=role,
            content=content,
            metadata=None if metadata is None else json.dumps(metadata),
            created_at=datetime.utcnow(),
        )
    )
    await db.execute(
        update(chat_sessions)
        .where(chat_sessions.c.id == session_id)
        .values(updated_at=datetime.utcnow())
    )


async def list_messages(db: Database, session_id: int) -> list[ChatMessagePayload]:
    rows = await db.fetch_all(
        select(chat_messages.c.role, chat_messages.c.content)
        .where(chat_messages.c.session_id == session_id)
        .order_by(chat_messages.c.created_at)
    )
    return [ChatMessagePayload(role=row["role"], content=row["content"]) for row in rows]


async def list_sessions(
    db: Database,
    *,
    user_id: int,
    task_id: Optional[int] = None,
    limit: int = 10,
):
    query = (
        select(chat_sessions)
        .where(chat_sessions.c.user_id == user_id)
        .order_by(chat_sessions.c.updated_at.desc())
        .limit(limit)
    )
    if task_id is not None:
        query = query.where(chat_sessions.c.task_id == task_id)
    rows = await db.fetch_all(query)
    return rows


async def get_session(db: Database, session_id: int, user_id: int):
    return await db.fetch_one(
        select(chat_sessions).where(
            (chat_sessions.c.id == session_id) & (chat_sessions.c.user_id == user_id)
        )
    )


async def get_session_messages(db: Database, session_id: int):
    query = (
        select(
            chat_messages.c.role,
            chat_messages.c.content,
            chat_messages.c.metadata,
            chat_messages.c.created_at,
        )
        .where(chat_messages.c.session_id == session_id)
        .order_by(chat_messages.c.created_at)
    )
    rows = await db.fetch_all(query)
    result = []
    for row in rows:
        meta = None
        if row["metadata"]:
            try:
                meta = json.loads(row["metadata"])
            except json.JSONDecodeError:
                meta = None
        result.append(
            {
                "role": row["role"],
                "content": row["content"],
                "metadata": meta,
                "created_at": row["created_at"],
            }
        )
    return result


async def get_latest_task_code(db: Database, task_id: int, user_id: int) -> Optional[str]:
    row = await db.fetch_one(
        select(analysis_tasks.c.generated_code)
        .where(analysis_tasks.c.id == task_id)
        .where(analysis_tasks.c.user_id == user_id)
    )
    if row and row["generated_code"]:
        return row["generated_code"]
    return None

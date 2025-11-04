from typing import Optional

from databases import Database
from sqlalchemy import insert, select

from ..models.user import users
from ..schemas import UserRead
from ..security import hash_password, verify_password


async def get_user_by_username(db: Database, username: str) -> Optional[UserRead]:
    row = await db.fetch_one(select(users).where(users.c.username == username))
    if not row:
        return None
    return UserRead.model_validate(row)


async def get_user_by_email(db: Database, email: str) -> Optional[UserRead]:
    row = await db.fetch_one(select(users).where(users.c.email == email))
    if not row:
        return None
    return UserRead.model_validate(row)


async def get_user_by_id(db: Database, user_id: int) -> Optional[UserRead]:
    row = await db.fetch_one(select(users).where(users.c.id == user_id))
    if not row:
        return None
    return UserRead.model_validate(row)


async def create_user(
    db: Database,
    *,
    username: str,
    password: str,
    email: Optional[str] = None,
) -> UserRead:
    hashed_password = hash_password(password)
    query = (
        insert(users)
        .values(username=username, email=email, password_hash=hashed_password)
        .returning(users)
    )
    row = await db.fetch_one(query)
    if not row:
        raise RuntimeError("Failed to create user.")
    return UserRead.model_validate(row)


async def authenticate_user(db: Database, username: str, password: str) -> Optional[UserRead]:
    row = await db.fetch_one(select(users).where(users.c.username == username))
    if not row:
        return None
    if not verify_password(password, row["password_hash"]):
        return None
    return UserRead.model_validate(row)

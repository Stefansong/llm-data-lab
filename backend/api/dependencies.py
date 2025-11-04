from fastapi import Depends, Header, HTTPException, status

from ..database import database
from ..models.user import users
from ..security import decode_access_token


async def get_database():
    """Provide a database connection for request scope."""
    yield database


async def get_current_user_id(
    authorization: str | None = Header(default=None),
    x_user_id: int | None = Header(default=None),
    db=Depends(get_database),
) -> int:
    """Resolve the current user id from a bearer token or explicit header."""
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="认证信息格式不正确。",
            )
        try:
            payload = decode_access_token(token)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="访问令牌无效或已过期。",
            ) from exc
        sub = payload.get("sub")
        if sub is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="访问令牌缺少用户标识。",
            )
        try:
            user_id = int(sub)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="访问令牌的用户标识无效。",
            ) from exc
        user = await db.fetch_one(users.select().where(users.c.id == user_id))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在或已被删除。",
            )
        return user_id

    if x_user_id is not None:
        if x_user_id <= 0:
            raise HTTPException(status_code=400, detail="Invalid user id provided.")
        user = await db.fetch_one(users.select().where(users.c.id == x_user_id))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在或已被删除。",
            )
        return x_user_id

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="请先登录后再执行此操作。",
    )

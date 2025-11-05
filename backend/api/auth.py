import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..api.dependencies import get_current_user_id, get_database
from ..schemas import (
    TokenResponse,
    UserLoginRequest,
    UserRead,
    UserRegisterRequest,
)
from ..security import create_access_token
from ..services import auth_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")  # 🔒 限制：每分钟最多 5 次注册请求
async def register_user(
    request: Request,
    payload: UserRegisterRequest,
    db=Depends(get_database)
) -> TokenResponse:
    """用户注册端点，受速率限制保护"""
    logger.info(f"Registration attempt for username: {payload.username}")

    existing = await auth_service.get_user_by_username(db, payload.username)
    if existing:
        logger.warning(f"Registration failed: username {payload.username} already exists")
        raise HTTPException(status_code=409, detail="该用户名已存在。")

    if payload.email:
        email_owner = await auth_service.get_user_by_email(db, payload.email)
        if email_owner:
            logger.warning(f"Registration failed: email {payload.email} already in use")
            raise HTTPException(status_code=409, detail="该邮箱已被使用。")

    try:
        user = await auth_service.create_user(
            db,
            username=payload.username,
            password=payload.password,
            email=payload.email,
        )
        logger.info(f"User registered successfully: {user.username} (ID: {user.id})")
    except ValueError as exc:
        logger.error(f"Registration failed for {payload.username}: {exc}")
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    token = create_access_token(subject=str(user.id), username=user.username)
    return TokenResponse(access_token=token, user=user)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")  # 🔒 限制：每分钟最多 10 次登录尝试
async def login_user(
    request: Request,
    payload: UserLoginRequest,
    db=Depends(get_database)
) -> TokenResponse:
    """用户登录端点，受速率限制保护"""
    logger.info(f"Login attempt for username: {payload.username}")

    user = await auth_service.authenticate_user(db, payload.username, payload.password)
    if not user:
        logger.warning(f"Login failed for username: {payload.username}")
        raise HTTPException(status_code=401, detail="用户名或密码错误。")

    logger.info(f"User logged in successfully: {user.username} (ID: {user.id})")
    token = create_access_token(subject=str(user.id), username=user.username)
    return TokenResponse(access_token=token, user=user)


@router.get("/me", response_model=UserRead)
async def get_me(db=Depends(get_database), user_id: int = Depends(get_current_user_id)) -> UserRead:
    user = await auth_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在。")
    return user

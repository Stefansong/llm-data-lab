from fastapi import APIRouter, Depends, HTTPException, status

from ..api.dependencies import get_current_user_id, get_database
from ..schemas import (
    TokenResponse,
    UserLoginRequest,
    UserRead,
    UserRegisterRequest,
)
from ..security import create_access_token
from ..services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_user(payload: UserRegisterRequest, db=Depends(get_database)) -> TokenResponse:
    existing = await auth_service.get_user_by_username(db, payload.username)
    if existing:
        raise HTTPException(status_code=409, detail="该用户名已存在。")
    if payload.email:
        email_owner = await auth_service.get_user_by_email(db, payload.email)
        if email_owner:
            raise HTTPException(status_code=409, detail="该邮箱已被使用。")

    try:
        user = await auth_service.create_user(
            db,
            username=payload.username,
            password=payload.password,
            email=payload.email,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    token = create_access_token(subject=str(user.id), username=user.username)
    return TokenResponse(access_token=token, user=user)


@router.post("/login", response_model=TokenResponse)
async def login_user(payload: UserLoginRequest, db=Depends(get_database)) -> TokenResponse:
    user = await auth_service.authenticate_user(db, payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误。")
    token = create_access_token(subject=str(user.id), username=user.username)
    return TokenResponse(access_token=token, user=user)


@router.get("/me", response_model=UserRead)
async def get_me(db=Depends(get_database), user_id: int = Depends(get_current_user_id)) -> UserRead:
    user = await auth_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在。")
    return user

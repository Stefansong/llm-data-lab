import base64
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import bcrypt
from cryptography.fernet import Fernet, InvalidToken
from jose import JWTError, jwt

from .config import get_settings

_fernet: Optional[Fernet] = None
_BCRYPT_MAX_BYTES = 72


def _ensure_password_length(password: str) -> None:
    if len(password.encode("utf-8")) > _BCRYPT_MAX_BYTES:
        raise ValueError("密码长度不可超过 72 字节（约 72 个英文字符或 36 个中文字符），请缩短后再试。")


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is not None:
        return _fernet
    settings = get_settings()
    secret_source = settings.credentials_secret_key or settings.jwt_secret_key
    digest = hashlib.sha256(secret_source.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    _fernet = Fernet(key)
    return _fernet


def hash_password(password: str) -> str:
    _ensure_password_length(password)
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str | None) -> bool:
    if not hashed_password:
        return False
    try:
        _ensure_password_length(plain_password)
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(
    *,
    subject: str,
    username: str,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    settings = get_settings()
    to_encode: Dict[str, Any] = {
        "sub": subject,
        "username": username,
    }
    if extra_claims:
        to_encode.update(extra_claims)

    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expires_minutes)
    )
    to_encode["exp"] = expire
    to_encode["iat"] = datetime.now(timezone.utc)

    return jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> Dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:  # pragma: no cover - library errors
        raise ValueError("Invalid access token") from exc
    return payload


def encrypt_secret(value: str | None) -> Optional[str]:
    if not value:
        return None
    fernet = _get_fernet()
    token = fernet.encrypt(value.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_secret(value: str | None) -> Optional[str]:
    if not value:
        return None
    fernet = _get_fernet()
    try:
        plaintext = fernet.decrypt(value.encode("utf-8"))
    except InvalidToken:
        return None
    return plaintext.decode("utf-8")

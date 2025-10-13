from datetime import datetime, timedelta
from typing import Optional, Union, Any
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

try:
    import bcrypt  # type: ignore
    import types

    if not hasattr(bcrypt, "__about__"):
        bcrypt.__about__ = types.SimpleNamespace(  # type: ignore[attr-defined]
            __version__=getattr(bcrypt, "__version__", "")
        )
except Exception:  # pragma: no cover - defensive fallback
    bcrypt = None  # type: ignore

# Support both bcrypt (default 2b, 12 rounds) and legacy bcrypt_sha256 hashes.
pwd_context = CryptContext(
    schemes=["bcrypt", "bcrypt_sha256"],
    deprecated="auto",
    bcrypt__rounds=12,
    bcrypt__ident="2b",
)


def create_access_token(
    subject: Union[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload.get("sub")
    except jwt.JWTError:
        return None

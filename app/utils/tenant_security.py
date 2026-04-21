# app/utils/tenant_security.py
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.config import settings
from app.models.tenant_models import TenantUser
from app.schemas.tenant_user_schemas import TokenData
from app.dependencies.tenant_db import get_tenant_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/tenant/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def authenticate_tenant_user(db: Session, email: str, password: str) -> Optional[TenantUser]:
    """Authenticate a tenant user"""
    user = db.query(TenantUser).filter(TenantUser.email == email).first()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


async def get_current_tenant_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_tenant_db)
) -> TenantUser:
    """Get the current authenticated tenant user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        is_tenant_user: bool = payload.get("is_tenant_user", False)

        if email is None or not is_tenant_user:
            raise credentials_exception

        token_data = TokenData(
            email=email,
            user_id=user_id,
            tenant_id=payload.get("tenant_id"),
            is_tenant_user=is_tenant_user
        )
    except JWTError:
        raise credentials_exception

    user = db.query(TenantUser).filter(TenantUser.email == token_data.email).first()
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_tenant_user(
    current_user: TenantUser = Depends(get_current_tenant_user)
) -> TenantUser:
    """Get the current active tenant user"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

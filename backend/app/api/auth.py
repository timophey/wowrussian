from datetime import datetime, timedelta
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.config import settings
from app.models.user import User
from app.schemas.user import UserCreate, User as UserSchema, Token, UserLogin
from app.utils.db import safe_scalar

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def authenticate_user(email: str, password: str, db: AsyncSession) -> User | None:
    """Authenticate user by email and password."""
    user = await safe_scalar(db, select(User).where(User.email == email))
    if not user:
        return None
    # TODO: Implement proper password verification with passlib
    # For now, we'll just check plain text (NOT PRODUCTION READY)
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    # TODO: Implement proper JWT encoding with python-jose
    # For now, return a simple string (NOT PRODUCTION READY)
    return f"fake-token-{data['sub']}"


@router.post("/register", response_model=UserSchema)
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user."""
    # Check if user exists
    existing = await safe_scalar(db, select(User).where(User.email == user.email))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user (TODO: hash password properly)
    new_user = User(
        email=user.email,
        password_hash=user.password  # THIS IS NOT SECURE - TODO: HASH!
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: AsyncSession = Depends(get_db)
):
    """Login and get access token."""
    user = await authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current user from token."""
    # TODO: Implement proper JWT verification
    # For now, just return first user (NOT PRODUCTION READY)
    user = await safe_scalar(db, select(User))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
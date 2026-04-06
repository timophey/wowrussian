from datetime import datetime, timedelta
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.database import get_db
from app.core.config import settings
from app.models.user import User
from app.models.project import Project
from app.models.page import Page
from app.models.foreign_word import ForeignWord
from app.models.russian_word import RussianWord
from app.models.guest_session import GuestSession
from app.models.export_job import ExportJob
from app.schemas.user import UserCreate, User as UserSchema, Token, UserLogin
from app.utils.db import safe_scalar

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash.
    Supports both bcrypt hashes and plain text (for legacy/development).
    
    Bcrypt has a maximum password length of 72 bytes, so we truncate
    longer passwords to match the hashing behavior.
    """
    # Truncate password to 72 bytes (bcrypt limitation) for consistent verification
    password_bytes = plain_password.encode('utf-8')
    if len(password_bytes) > 72:
        plain_password = password_bytes[:72].decode('utf-8', errors='ignore')
    
    # If hash doesn't look like a bcrypt hash, treat as plain text
    if not hashed_password.startswith('$2b$') and not hashed_password.startswith('$2a$'):
        # Legacy: plain text comparison
        return plain_password == hashed_password
    # Use passlib for bcrypt hashes
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password.
    
    Bcrypt has a maximum password length of 72 bytes, so we truncate
    longer passwords to prevent ValueError.
    """
    # Truncate password to 72 bytes (bcrypt limitation)
    # Using UTF-8 encoding to properly count bytes
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password = password_bytes[:72].decode('utf-8', errors='ignore')
    return pwd_context.hash(password)


async def authenticate_user(email: str, password: str, db: AsyncSession) -> User | None:
    """Authenticate user by email and password."""
    user = await safe_scalar(db, select(User).where(User.email == email))
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


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
    
    # Hash password before storing
    hashed_password = get_password_hash(user.password)
    
    # Create new user with hashed password
    new_user = User(
        email=user.email,
        password_hash=hashed_password
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


@router.get("/me", response_model=UserSchema)
async def get_current_user_endpoint(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db)
):
    """Get current user information."""
    return await get_current_user(token, db)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await safe_scalar(db, select(User).where(User.id == int(user_id)))
    if user is None:
        raise credentials_exception
    return user


async def get_optional_user(
    token: str | None,
    db: AsyncSession
) -> User | None:
    """Get current user if token is valid, otherwise return None."""
    if not token:
        return None
    try:
        return await get_current_user(token, db)
    except HTTPException:
        return None


@router.post("/me/delete-account", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete current user's account and all associated data.
    
    This endpoint implements the right to erasure (right to be forgotten)
    as required by 152-FZ Article 21 and GDPR Article 17.
    """
    # Delete all associated projects (cascade will handle related data)
    await db.execute(
        delete(Project).where(Project.owner_id == current_user.id)
    )
    
    # Delete export jobs
    await db.execute(
        delete(ExportJob).where(ExportJob.owner_id == current_user.id)
    )
    
    # Delete the user
    await db.execute(delete(User).where(User.id == current_user.id))
    await db.commit()
    
    return None


@router.post("/guest/delete-session", status_code=status.HTTP_204_NO_CONTENT)
async def delete_guest_session(
    session_token: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete guest session and all associated data.
    
    This endpoint implements the right to erasure for guest users.
    """
    # Find the guest session
    result = await db.execute(
        select(GuestSession).where(GuestSession.session_token == session_token)
    )
    guest_session = result.scalar_one_or_none()
    
    if not guest_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Guest session not found"
        )
    
    # Delete all associated projects (cascade will handle related data)
    await db.execute(
        delete(Project).where(Project.guest_session_id == guest_session.id)
    )
    
    # Delete the guest session
    await db.execute(delete(GuestSession).where(GuestSession.id == guest_session.id))
    await db.commit()
    
    return None


@router.get("/legal-info")
async def get_legal_info():
    """Get legal information about the data operator.
    
    This endpoint provides information required by 152-FZ Article 18.1
    about the personal data operator.
    """
    # Build operator info - only include non-empty fields
    operator_info = {}
    if settings.operator_name:
        operator_info["name"] = settings.operator_name
    if settings.operator_inn:
        operator_info["inn"] = settings.operator_inn
    if settings.operator_ogrn:
        operator_info["ogrn"] = settings.operator_ogrn
    if settings.operator_address:
        operator_info["address"] = settings.operator_address
    if settings.operator_email:
        operator_info["email"] = settings.operator_email
    
    return {
        "operator": operator_info,
        "privacy_policy_url": "/privacy-policy",
        "law_reference": "Federal Law No. 152-FZ dated July 27, 2006 'On Personal Data'"
    }
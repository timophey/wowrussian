from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, text
from pydantic import BaseModel, EmailStr, Field

from app.core.database import get_db
from app.core.config import settings
from app.models.user import User
from app.models.project import Project
from app.schemas.user import UserCreate, User as UserSchema

router = APIRouter(prefix="/admin", tags=["admin"])


class AdminAuth(BaseModel):
    """Model for admin authentication via header."""
    admin_key: str = Field(..., alias="X-Admin-Key")


async def verify_admin_access(request: Request) -> bool:
    """Verify admin access via header or query parameter."""
    admin_key = request.headers.get("X-Admin-Key")
    if not admin_key:
        admin_key = request.query_params.get("admin_key")
    
    if not admin_key or admin_key != settings.admin_secret_key:
        return False
    return True


async def get_admin_user(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> User:
    """Dependency to verify admin access and return admin user (first user)."""
    if not await verify_admin_access(request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing admin key"
        )
    # Return first user as admin (or could return a special admin marker)
    admin = await db.execute(select(User).limit(1))
    user = admin.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No users found in system"
        )
    return user


@router.get("/users", response_model=List[UserSchema])
async def list_users(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: User = Depends(get_admin_user)
):
    """List all users with their project counts."""
    # Get all users with project counts
    result = await db.execute(
        select(
            User,
            func.count(Project.id).label("project_count")
        )
        .outerjoin(Project, User.id == Project.user_id)
        .group_by(User.id)
        .order_by(User.id)
    )
    
    users_data = []
    for user, project_count in result.all():
        user_dict = {
            "id": user.id,
            "email": user.email,
            "created_at": user.created_at
        }
        users_data.append(user_dict)
    
    return users_data


@router.post("/users", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: Request,
    user: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: User = Depends(get_admin_user)
):
    """Create a new user."""
    # Check if user exists
    existing = await db.execute(
        select(User).where(User.email == user.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Get next ID from sequence to avoid PostgreSQL sequence sync issues
    # This ensures we always use an available ID
    result = await db.execute(text("SELECT nextval('users_id_seq')"))
    next_id = result.scalar_one()
    
    # Create new user with explicit ID
    new_user = User(
        id=next_id,
        email=user.email,
        password_hash=user.password
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    return new_user


@router.delete("/users/{user_id}")
async def delete_user(
    request: Request,
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: User = Depends(get_admin_user)
):
    """Delete a user and all their projects."""
    # Find user
    user = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = user.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent deleting the last admin (first user)
    if user_id == 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the primary admin user"
        )
    
    # Delete user (cascade will handle projects)
    await db.delete(user)
    await db.commit()
    
    return {"message": "User deleted successfully"}

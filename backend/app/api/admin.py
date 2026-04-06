from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, text
from pydantic import BaseModel, EmailStr, Field
from jose import JWTError, jwt

from app.core.database import get_db
from app.core.config import settings
from app.models.user import User, UserRole
from app.models.project import Project, ProjectStatus
from app.schemas.user import UserCreate, User as UserSchema, UserUpdate
from app.schemas.project import Project as ProjectSchema
from app.api.auth import get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


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
    """Dependency to verify admin access via admin key and return admin user (first user)."""
    if not await verify_admin_access(request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing admin key"
        )
    # Return first user as admin (legacy behavior)
    admin = await db.execute(select(User).limit(1))
    user = admin.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No users found in system"
        )
    return user


async def get_admin_or_role_admin(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[str | None, Depends(oauth2_scheme)] = None
) -> User:
    """Dependency that supports both admin key and role-based admin authentication.
    
    First tries to authenticate via admin key (legacy), then falls back to
    JWT token with admin role check.
    """
    # Try admin key authentication first
    if await verify_admin_access(request):
        admin = await db.execute(select(User).limit(1))
        user = admin.scalar_one_or_none()
        if user:
            return user
    
    # Fall back to JWT token authentication with admin role check
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
    
    user_result = await db.execute(select(User).where(User.id == int(user_id)))
    user = user_result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    # Check admin role
    user_role = user.role
    if isinstance(user_role, UserRole):
        user_role = user_role.value
    
    if user_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    return user


class UserProjectsResponse(BaseModel):
    """Response model for user's projects."""
    user: UserSchema
    projects: List[dict]
    total_projects: int


class UserRoleUpdate(BaseModel):
    """Schema for updating user role."""
    role: str


@router.get("/users", response_model=List[UserSchema])
async def list_users(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: User = Depends(get_admin_or_role_admin)
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
            "role": user.role.value if hasattr(user.role, 'value') else user.role,
            "created_at": user.created_at
        }
        users_data.append(user_dict)
    
    return users_data


@router.post("/users", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: Request,
    user: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: User = Depends(get_admin_or_role_admin)
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
    _: User = Depends(get_admin_or_role_admin)
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


@router.patch("/users/{user_id}/role", response_model=UserSchema)
async def update_user_role(
    request: Request,
    user_id: int,
    role_update: UserRoleUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: User = Depends(get_admin_or_role_admin)
):
    """Update a user's role. Only admins can do this."""
    # Find user
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Validate role
    valid_roles = ["user", "admin"]
    if role_update.role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {valid_roles}"
        )
    
    # Prevent removing admin role from the primary admin
    if user_id == 1 and role_update.role == "user":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove admin role from primary admin"
        )
    
    # Update role
    user.role = UserRole(role_update.role)
    await db.commit()
    await db.refresh(user)
    
    return user


@router.get("/users/{user_id}/projects", response_model=UserProjectsResponse)
async def get_user_projects(
    request: Request,
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: User = Depends(get_admin_or_role_admin)
):
    """Get all projects for a specific user."""
    # Find user
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get user's projects
    projects_result = await db.execute(
        select(Project)
        .where(Project.user_id == user_id)
        .order_by(Project.created_at.desc())
    )
    projects = projects_result.scalars().all()
    
    projects_data = []
    for project in projects:
        project_dict = {
            "id": project.id,
            "domain": project.domain,
            "base_url": project.base_url,
            "status": project.status.value if hasattr(project.status, 'value') else project.status,
            "stats": project.stats,
            "created_at": project.created_at,
            "updated_at": project.updated_at
        }
        projects_data.append(project_dict)
    
    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role.value if hasattr(user.role, 'value') else user.role,
            "created_at": user.created_at
        },
        "projects": projects_data,
        "total_projects": len(projects_data)
    }


@router.post("/migrate-admin-role", response_model=UserSchema)
async def migrate_admin_role(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Migrate the admin key-based access to role-based admin.
    
    This endpoint allows the first user to become an admin by role,
    enabling them to log in normally and still have admin access.
    
    After calling this, the first user will have the 'admin' role
    and can use regular JWT authentication for admin endpoints.
    """
    if not await verify_admin_access(request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing admin key"
        )
    
    # Get first user
    result = await db.execute(select(User).order_by(User.id).limit(1))
    first_user = result.scalar_one_or_none()
    
    if not first_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No users found in system"
        )
    
    # Set admin role
    first_user.role = UserRole.ADMIN
    await db.commit()
    await db.refresh(first_user)
    
    return first_user

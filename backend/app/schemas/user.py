from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class UserRoleEnum(str, Enum):
    """User role enum for API schema."""
    user = "user"
    admin = "admin"


class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class User(UserBase):
    id: int
    role: UserRoleEnum = UserRoleEnum.user
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class UserUpdate(BaseModel):
    """Schema for updating user fields."""
    role: Optional[UserRoleEnum] = None


class PasswordChange(BaseModel):
    """Schema for changing password."""
    current_password: str
    new_password: str = Field(..., min_length=8)
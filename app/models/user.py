"""
User and authentication Pydantic models
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from uuid import UUID


class User(BaseModel):
    """User database model"""
    id: UUID
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool = True
    is_admin: bool = False
    created_at: datetime


class UserCreate(BaseModel):
    """Model for user creation"""
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    is_admin: bool = False


class UserLogin(BaseModel):
    """Model for user login"""
    username: str = Field(..., description="Email address for login")
    password: str


class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token payload data"""
    sub: str = Field(..., description="Subject (user ID)")
    exp: Optional[datetime] = None

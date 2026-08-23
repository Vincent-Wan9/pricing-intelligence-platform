from datetime import datetime
from typing import Optional, Literal
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field



class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    first_name: Optional[str] = Field(default=None, max_length=100)
    last_name: Optional[str] = Field(default=None, max_length=100)
    role: Literal["admin", "approver", "editor", "viewer"] = "viewer"
    is_active: bool = True


class CreateUserSchema(UserBase):
    password: str = Field(..., min_length=8)
 

class UpdateUserSchema(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(default=None, min_length=3, max_length=100)
    first_name: Optional[str] = Field(default=None, max_length=100)
    last_name: Optional[str] = Field(default=None, max_length=100)
    role: Optional[Literal["admin", "approver", "editor", "viewer"]] = None
    is_active: Optional[bool] = None


class UserPublic(UserBase):
    user_id: UUID
    last_login: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DeleteUserSchema(BaseModel):
    detail: str



class LoginSchema(BaseModel):
    # OAuth calls the form field ``username``; it may contain either login key.
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ChangePasswordSchema(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)

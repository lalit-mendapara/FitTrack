from pydantic import BaseModel,Field
from datetime import date
from typing import Literal,Optional
import re

EMAIL_REGX = r"^[^@]+@[^@]+\.[^@]+$"



# Schema for creating user
class UserCreate(BaseModel):
    name: str
    email: str = Field(...,pattern=EMAIL_REGX)
    password: str
    dob: date
    gender: str

# Schema for login (JSON body)
class UserLogin(BaseModel):
    email: str = Field(..., pattern=EMAIL_REGX)
    password: str

# Schema for updating user
class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = Field(None, pattern=EMAIL_REGX)
    dob: Optional[date] = None
    gender: Optional[str] = None
    password: Optional[str] = None
    old_password: Optional[str] = None

# Schema for returning user (without password)
class UserResponse(BaseModel):
    id: int
    name: str
    email: str = Field(...,pattern=EMAIL_REGX)
    dob: date
    gender: str
    age: int

    class Config:
        from_attributes = True  # Changed from orm_mode in Pydantic v2

# Schema for signup response
class UserSignupResponse(BaseModel):
    user: UserResponse
    access_token: str
    token_type: str
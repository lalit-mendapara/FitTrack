from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from typing import List, Any
from datetime import timedelta

from app.utils.utils import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, verify_password
from app.database import get_db
from app.schemas.user import UserCreate, UserResponse, UserUpdate, UserSignupResponse
from app.crud import user as crud_user
from app.models.user import User
from app.api.auth import get_current_user

router = APIRouter(prefix="/users", tags=["users"])

# POST - Signup (Create new user + Login)
@router.post("/signup", response_model=UserSignupResponse, status_code=status.HTTP_201_CREATED)
def signup(
    response: Response,
    user: UserCreate, 
    db: Session = Depends(get_db)
):
    # Check if email already exists
    db_user = crud_user.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(
            status_code=400, 
            detail="Email already registered"
        )
    
    # Create user
    new_user = crud_user.create_user(db=db, user=user)
    
    # Generate Token
    access_token = create_access_token(
        data={"sub": new_user.email}
    )
    
    # Set Cookie
    response.set_cookie(
        key="access_token",
        value=f"{access_token}",
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        expires=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=False 
    )
    
    return {
        "user": new_user,
        "access_token": access_token,
        "token_type": "bearer"
    }

# GET - Get current user
@router.get("/me", response_model=UserResponse)
def read_me(current_user: User = Depends(get_current_user)):
    return current_user

# PUT - Update current user
@router.put("/me", response_model=UserResponse)
def update_me(
    user_update: UserUpdate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # If updating password, verify old password
    if user_update.password:
        if not user_update.old_password:
             raise HTTPException(
                status_code=400,
                detail="Old password is required to change password"
            )
        if not verify_password(user_update.old_password, current_user.password):
             raise HTTPException(
                status_code=400,
                detail="Incorrect old password"
            )

    db_user = crud_user.update_user(db, user_id=current_user.id, user_update=user_update)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

# DELETE - Delete current user
@router.delete("/me")
def delete_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    crud_user.delete_user(db, user_id=current_user.id)
    return {"message": "User deleted successfully"}
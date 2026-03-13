from fastapi import APIRouter, Depends, HTTPException, status, Response, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Any
from datetime import timedelta
import os
import time
import shutil

from app.utils.utils import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, verify_password
from app.database import get_db
from app.schemas.user import UserCreate, UserResponse, UserUpdate, UserSignupResponse
from app.crud import user as crud_user
from app.models.user import User
from app.api.auth import get_current_user

AVATAR_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "uploads", "avatars")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

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

# POST - Upload Avatar
@router.post("/upload-avatar")
def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Validate file extension
    _, ext = os.path.splitext(file.filename)
    ext = ext.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Validate file size
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Max 5MB.")

    # Ensure directory exists
    os.makedirs(AVATAR_DIR, exist_ok=True)

    # Delete old avatar if exists
    if current_user.profile_picture_url:
        old_filename = current_user.profile_picture_url.split("/")[-1]
        old_path = os.path.join(AVATAR_DIR, old_filename)
        if os.path.exists(old_path):
            os.remove(old_path)

    # Save new file
    filename = f"{current_user.id}_{int(time.time())}{ext}"
    file_path = os.path.join(AVATAR_DIR, filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Update DB
    avatar_url = f"/uploads/avatars/{filename}"
    current_user.profile_picture_url = avatar_url
    db.commit()
    db.refresh(current_user)

    return {"profile_picture_url": avatar_url}

# DELETE - Delete current user
@router.delete("/me")
def delete_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    crud_user.delete_user(db, user_id=current_user.id)
    return {"message": "User deleted successfully"}
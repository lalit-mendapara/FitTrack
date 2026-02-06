from fastapi import APIRouter, Depends, HTTPException, status, Response, Body
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import Any

from app.database import get_db
from app.crud import user as crud_user
from app.utils.utils import verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from app.schemas.user import UserLogin

router = APIRouter(tags=["login"])

@router.post("/login", response_model=Any)
def login_for_access_token(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    user = crud_user.get_user_by_email(db, email=form_data.username)
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}
    )
    
    # Set cookie for browser-based access (optional but good for web apps)
    response.set_cookie(
        key="access_token",
        value=f"{access_token}",
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        expires=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=False # Set to True in production (HTTPS)
    )
    
    return {"access_token": access_token, "token_type": "bearer", "user_id": user.id}

@router.post("/login/json", response_model=Any)
def login_json(
    response: Response,
    login_data: UserLogin,
    db: Session = Depends(get_db)
):
    """
    JSON-based login for API clients that prefer JSON body over Form Data.
    """
    user = crud_user.get_user_by_email(db, email=login_data.email)
    if not user or not verify_password(login_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(
        data={"sub": user.email}
    )
    
    # Set cookie
    response.set_cookie(
        key="access_token",
        value=f"{access_token}",
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        expires=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=False 
    )
    
    return {"access_token": access_token, "token_type": "bearer", "user_id": user.id}

@router.post("/login/logout")
def logout(response: Response):
    """
    Logout the user by clearing the access_token cookie.
    """
    response.delete_cookie("access_token")
    return {"message": "Logged out successfully"}

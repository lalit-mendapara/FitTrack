from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.admin import AdminLogin, AdminToken, AdminResponse
from app.crud.admin import authenticate_admin, update_admin_last_login
from app.utils.admin_auth import create_admin_access_token, get_current_admin
from app.models.admin import Admin

router = APIRouter(prefix="/api/admin", tags=["Admin Auth"])

@router.post("/login", response_model=AdminToken)
async def admin_login(credentials: AdminLogin, db: Session = Depends(get_db)):
    admin = authenticate_admin(db, credentials.email, credentials.password)
    
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    update_admin_last_login(db, admin.id)
    
    access_token = create_admin_access_token(data={"sub": str(admin.id)})
    
    return AdminToken(
        access_token=access_token,
        admin=AdminResponse.model_validate(admin)
    )

@router.get("/me", response_model=AdminResponse)
async def get_current_admin_info(current_admin: Admin = Depends(get_current_admin)):
    return AdminResponse.model_validate(current_admin)

@router.post("/logout")
async def admin_logout(current_admin: Admin = Depends(get_current_admin)):
    return {"message": "Successfully logged out"}

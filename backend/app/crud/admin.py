from sqlalchemy.orm import Session
from app.models.admin import Admin
from app.schemas.admin import AdminCreate, AdminUpdate
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from typing import Optional
from datetime import datetime

ph = PasswordHasher()

def get_password_hash(password: str) -> str:
    return ph.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        ph.verify(hashed_password, plain_password)
        return True
    except VerifyMismatchError:
        return False

def get_admin_by_email(db: Session, email: str) -> Optional[Admin]:
    return db.query(Admin).filter(Admin.email == email).first()

def get_admin_by_id(db: Session, admin_id: int) -> Optional[Admin]:
    return db.query(Admin).filter(Admin.id == admin_id).first()

def create_admin(db: Session, admin: AdminCreate) -> Admin:
    hashed_password = get_password_hash(admin.password)
    db_admin = Admin(
        email=admin.email,
        hashed_password=hashed_password,
        full_name=admin.full_name,
        is_super_admin=admin.is_super_admin
    )
    db.add(db_admin)
    db.commit()
    db.refresh(db_admin)
    return db_admin

def authenticate_admin(db: Session, email: str, password: str) -> Optional[Admin]:
    admin = get_admin_by_email(db, email)
    if not admin:
        return None
    if not verify_password(password, admin.hashed_password):
        return None
    if not admin.is_active:
        return None
    return admin

def update_admin_last_login(db: Session, admin_id: int) -> None:
    admin = get_admin_by_id(db, admin_id)
    if admin:
        admin.last_login = datetime.utcnow()
        db.commit()

def update_admin(db: Session, admin_id: int, admin_update: AdminUpdate) -> Optional[Admin]:
    admin = get_admin_by_id(db, admin_id)
    if not admin:
        return None
    
    update_data = admin_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(admin, field, value)
    
    db.commit()
    db.refresh(admin)
    return admin

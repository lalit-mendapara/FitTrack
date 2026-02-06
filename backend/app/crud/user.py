from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.utils.utils import hash_password,verify_password,create_access_token
from datetime import date

def get_user(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(User).offset(skip).limit(limit).all()

def create_user(db: Session, user: UserCreate):
    # Calculate age from dob
    today = date.today()
    age = today.year - user.dob.year - ((today.month, today.day) < (user.dob.month, user.dob.day))

    # Hash the password
    hashed_password = hash_password(user.password)
    
    db_user = User(
        name=user.name,
        email=user.email,
        password=hashed_password,  # In real app, hash this!
        dob=user.dob,
        gender=user.gender,
        age=age
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, user_id: int, user_update: UserUpdate):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        return None
    
    update_data = user_update.model_dump(exclude_unset=True)
    
    # Update age if dob is changed
    if 'dob' in update_data:
        today = date.today()
        new_dob = update_data['dob']
        if new_dob:
             update_data['age'] = today.year - new_dob.year - ((today.month, today.day) < (new_dob.month, new_dob.day))
    
    # Remove old_password if present (it's not in the DB)
    if 'old_password' in update_data:
        del update_data['old_password']
    
    # Hash password if it's being updated
    if 'password' in update_data and update_data['password']:
        update_data['password'] = hash_password(update_data['password'])
    elif 'password' in update_data:
        del update_data['password'] # Don't update if empty

    for field, value in update_data.items():
        setattr(db_user, field, value)
    
    db.commit()
    db.refresh(db_user)
    return db_user

def delete_user(db: Session, user_id: int):
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user:
        db.delete(db_user)
        db.commit()
    return db_user
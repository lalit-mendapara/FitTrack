from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyCookie
from jose import JWTError, jwt
from config import SECRET_KEY,ALGORITHM
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User

oauth2_scheme = APIKeyCookie(name="access_token")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Session expired. Please re-login.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        # This handles ExpiredSignatureError and other JWT issues
        raise credentials_exception

    # Check if user still exists in DB
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
        
    return user
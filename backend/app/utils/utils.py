from argon2 import PasswordHasher
from jose import JWTError,jwt
from argon2.exceptions import VerifyMismatchError
from datetime import datetime,timedelta,timezone
from config import SECRET_KEY,ALGORITHM

# Argon2 password hasher (OWASP recommended)
pwd_hasher = PasswordHasher(
    time_cost=2,
    memory_cost=102400,  # 100 MB
    parallelism=8,
    hash_len=32,
    salt_len=16,
)

# --- JWT Config ---
SECRET_KEY = SECRET_KEY  # Use a strong random string
ALGORITHM = ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # Session duration

def hash_password(password: str) -> str:
    return pwd_hasher.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_hasher.verify(hashed_password, plain_password)
    except VerifyMismatchError:
        return False
    
# Token Logic
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=1440)
    to_encode.update({'exp':expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

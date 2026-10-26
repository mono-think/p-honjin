from datetime import datetime, timedelta, timezone
import jwt
import bcrypt  # passlibの代わりにbcryptを直接インポート

# セキュリティ設定
SECRET_KEY = "your-super-secret-key-for-honjin"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """入力されたパスワードと、DBのハッシュ化パスワードを照合する"""
    # bcryptはバイト列で処理するためエンコードして比較します
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )

def get_password_hash(password: str) -> str:
    """平文のパスワードをハッシュ化する"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    # DB保存用に文字列(str)に戻して返す
    return hashed.decode('utf-8')

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """JWTアクセストークンを生成する"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel import Session, select, SQLModel
from typing import Annotated
from pydantic import BaseModel

# 独自のモジュールをインポート
from app.database import engine
from app.models import Company, Department, Personal, Account, SessionRecord
from app.security import verify_password, get_password_hash, create_access_token
from app.encryption import encrypt_pii, decrypt_pii, generate_blind_index  # ← 暗号化モジュールを追加

app = FastAPI(
    title="Project Honjin API",
    description="洋上プラント構想に基づくコアAPI",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json"
)

@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)

@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "Honjin Backend is running."}

def get_session():
    with Session(engine) as session:
        yield session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")


# ==========================================
# 1. テストユーザー登録API (PII暗号化版)
# ==========================================
class RegisterRequest(BaseModel):
    email: str
    password: str

@app.post("/api/register")
def register(req: RegisterRequest, session: Session = Depends(get_session)):
    # 1. 平文メールアドレスから「検索用ブラインドインデックス」を生成
    email_bidx = generate_blind_index(req.email)
    
    # DB検索にはブラインドインデックスを使用
    existing = session.exec(select(Personal).where(Personal.email_bidx == email_bidx)).first()
    if existing:
        raise HTTPException(status_code=400, detail="このメールアドレスは既に登録されています")
    
    # 2. 保存用の「暗号化データ（AES-GCM）」を生成
    email_enc = encrypt_pii(req.email)

    # Personal (個人情報枠) の作成。平文は一切保存しません
    new_personal = Personal(
        email_encrypted=email_enc,
        email_bidx=email_bidx
    )
    session.add(new_personal)
    session.flush()

    # Account (認証情報枠) の作成。ログインIDとしても平文を避け、ブラインドインデックスを保存します
    new_account = Account(
        personal_id=new_personal.id,
        provider="local",
        provider_account_id=email_bidx,
        password_hash=get_password_hash(req.password)
    )
    session.add(new_account)
    session.commit()
    
    return {"message": "ユーザー登録完了", "personal_id": new_personal.id}


# ==========================================
# 2. 認証API (PII暗号化版)
# ==========================================
@app.post("/api/login")
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Session = Depends(get_session)
):
    # 送信されたメールアドレス(username)をブラインドインデックス化してから検索
    login_bidx = generate_blind_index(form_data.username)
    account = session.exec(select(Account).where(Account.provider_account_id == login_bidx)).first()
    
    if not account or not account.password_hash:
        raise HTTPException(status_code=401, detail="メールアドレスまたはパスワードが間違っています")
    
    if not verify_password(form_data.password, account.password_hash):
        raise HTTPException(status_code=401, detail="メールアドレスまたはパスワードが間違っています")

    access_token = create_access_token(data={"sub": str(account.personal_id)})
    return {"access_token": access_token, "token_type": "bearer"}


# ==========================================
# 3. 鍵付きルートのテスト (復号化テスト)
# ==========================================
def get_current_user_id(token: Annotated[str, Depends(oauth2_scheme)]) -> int:
    from app.security import SECRET_KEY, ALGORITHM
    import jwt
    from jwt.exceptions import InvalidTokenError

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise HTTPException(status_code=401, detail="無効なトークン")
        return int(user_id_str)
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="無効な認証情報", headers={"WWW-Authenticate": "Bearer"})

@app.get("/api/me")
def read_users_me(
    current_user_id: Annotated[int, Depends(get_current_user_id)],
    session: Session = Depends(get_session)
):
    user = session.exec(select(Personal).where(Personal.id == current_user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
    
    # 3. データベースの暗号化データを復号化して平文に戻す
    decrypted_email = decrypt_pii(user.email_encrypted)
    
    return {
        "message": "認証成功",
        "personal_id": user.id,
        "public_id": user.public_id,
        "email_decrypted": decrypted_email  # 復号化された平文をレスポンスに含める
    }
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlmodel import SQLModel
from app.database import engine
from app.models import Company, Department, Personal, Account, SessionRecord

app = FastAPI(
    title="Project Honjin API",
    description="洋上プラント構想に基づくコアAPI",
    version="1.0.0"
)

@app.on_event("startup")
def on_startup():
    # 起動時にデータベースのテーブルを自動生成
    SQLModel.metadata.create_all(engine)

@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "Honjin Backend is running."}

# ==========================================
# 認証API (仮実装)
# ==========================================
class LoginRequest(BaseModel):
    email: str
    password: str

@app.post("/api/login")
def login(req: LoginRequest):
    # 今回はフロントエンドからの疎通確認のため、固定のID/パスワード
    if req.email == "test@example.com" and req.password == "password":
        # 成功時はダミートークンを返す
        return {"token": "honjin-dummy-token-12345"}
    
    # 失敗時は401エラー
    raise HTTPException(status_code=401, detail="メールアドレスまたはパスワードが違います")

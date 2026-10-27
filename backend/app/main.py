from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel import Session, select, SQLModel
from typing import Annotated
from pydantic import BaseModel
from app.database import engine
from app.models import Company, Department, Personal, Account, SessionRecord, AuditLog, OvertimeRequest
from app.security import verify_password, get_password_hash, create_access_token, SECRET_KEY, ALGORITHM
from app.encryption import encrypt_pii, decrypt_pii, generate_blind_index  # ← 暗号化モジュールを追加
from datetime import datetime, timezone, time
from zoneinfo import ZoneInfo
from app.logger import logger
from app.redis_client import redis_client
import jwt
from jwt.exceptions import InvalidTokenError

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
        email_bidx=email_bidx,
        company_id=1,
        department_id=1
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

    if redis_client.get(f"blacklist:{token}"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ログアウト済みのトークンです",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise HTTPException(status_code=401, detail="無効なトークン")
        return int(user_id_str)
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="無効な認証情報", headers={"WWW-Authenticate": "Bearer"})

def verify_working_hours(
    request: Request,
    current_user_id: int = Depends(get_current_user_id),
    session: Session = Depends(get_session)
) -> int:
    """業務時間内か、または時間外申請が承認されているかを確認する門番"""
    
    # ユーザー情報とアカウント情報を取得
    user = session.exec(select(Personal).where(Personal.id == current_user_id)).first()
    account = session.exec(select(Account).where(Account.personal_id == current_user_id)).first()
    
    if not user or not account:
        raise HTTPException(status_code=401, detail="ユーザーが存在しません")

    # 1. 緊急バイパス権限の確認
    if account.emergency_bypass_enabled:
        logger.info(f"緊急バイパス発動: {user.id}")
        return current_user_id

    # 2. 所属組織（Company or Department）の業務時間とタイムゾーンを取得
    # ※ 本来はDepartmentがあればそちらを優先しますが、ここでは簡略化のためCompanyを取得します
    company = session.exec(select(Company).where(Company.id == user.company_id)).first()
    
    # 所属未定や時間設定がない場合は一旦通す（またはデフォルト時間を設定）
    if not company or not company.work_start_time or not company.work_end_time:
        return current_user_id

    # 3. 現在の時間を組織のタイムゾーンで取得
    tz = ZoneInfo(company.timezone or "Asia/Tokyo")
    now_local = datetime.now(tz)
    current_time = now_local.time()
    current_date = now_local.date()

    # 4. 業務時間内か判定
    is_work_hour = company.work_start_time <= current_time <= company.work_end_time

    if is_work_hour:
        return current_user_id

    # 5. 業務時間外の場合、承認済みの事前申請（OvertimeRequest）があるか確認
    statement = select(OvertimeRequest).where(
        (OvertimeRequest.personal_id == current_user_id) &
        (OvertimeRequest.target_date == current_date) &
        (OvertimeRequest.status == "approved") &
        (OvertimeRequest.start_time <= current_time) &
        (OvertimeRequest.end_time >= current_time)
    )
    approved_request = session.exec(statement).first()

    if approved_request:
        logger.info(f"時間外アクセス許可 (申請ID: {approved_request.id}): {user.id}")
        return current_user_id

    # 6. 全てNGなら、監査ログ(DB)とログファイルに記録してアクセス遮断(403)
    client_ip = request.client.host if request.client else "unknown"
    
    audit_log = AuditLog(
        personal_id=current_user_id,
        action="LOGIN_BLOCKED_OUT_OF_HOURS",
        ip_address=client_ip,
        details='{"reason": "Outside working hours and no approved request"}'
    )
    session.add(audit_log)
    session.commit()

    logger.warning(
        "業務時間外の不正アクセスを遮断しました",
        extra={"extra_data": {"user_id": current_user_id, "ip": client_ip}}
    )
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="業務時間外です。事前の作業申請を行ってください。"
    )

@app.get("/api/me")
def read_users_me(
    # get_current_user_id の代わりに verify_working_hours を使う
    current_user_id: Annotated[int, Depends(verify_working_hours)],
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

@app.post("/api/logout")
def logout(token: Annotated[str, Depends(oauth2_scheme)]):
    try:
        # トークンの有効期限(exp)を取得
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp = payload.get("exp")
        
        if exp:
            # 現在時刻からの残り秒数を計算
            now = datetime.now(timezone.utc).timestamp()
            ttl = int(exp - now)
            
            if ttl > 0:
                # Redisに「このトークンは無効」として記録（寿命が来たら自動消滅）
                redis_client.setex(f"blacklist:{token}", ttl, "true")
                
    except jwt.InvalidTokenError:
        pass # すでに無効なトークンなら何もしない
        
    return {"message": "ログアウトしました"}

@app.get("/api/work-status")
def get_work_status(
    current_user_id: int = Depends(get_current_user_id),
    session: Session = Depends(get_session)
):
    """現在の業務時間ステータスと、残り時間をフロントエンドへ返す"""
    user = session.exec(select(Personal).where(Personal.id == current_user_id)).first()
    company = session.exec(select(Company).where(Company.id == user.company_id)).first()

    if not company or not company.work_end_time:
        return {"status": "unlimited", "remaining_seconds": None}

    tz = ZoneInfo(company.timezone or "Asia/Tokyo")
    now_local = datetime.now(tz)
    
    # 今日の終業時刻をdatetime型に合成
    end_datetime = datetime.combine(now_local.date(), company.work_end_time, tzinfo=tz)
    
    # 既に終業時刻を過ぎている場合は、承認済み残業申請（OvertimeRequest）の終了時刻を取得
    if now_local > end_datetime:
        overtime = session.exec(
            select(OvertimeRequest).where(
                (OvertimeRequest.personal_id == current_user_id) &
                (OvertimeRequest.target_date == now_local.date()) &
                (OvertimeRequest.status == "approved") &
                (OvertimeRequest.end_time >= now_local.time())
            )
        ).first()
        
        if overtime:
            end_datetime = datetime.combine(now_local.date(), overtime.end_time, tzinfo=tz)
        else:
            return {"status": "out_of_hours", "remaining_seconds": 0}

    # 残り時間を計算
    remaining_seconds = int((end_datetime - now_local).total_seconds())

    return {
        "status": "working",
        "remaining_seconds": remaining_seconds, # フロントはこの秒数を見てカウントダウンする
        "end_time": end_datetime.isoformat()
    }

@app.post("/api/setup-test-data", tags=["Setup"])
def setup_test_data(session: Session = Depends(get_session)):
    # """テスト用の企業と部署データを自動生成する"""
    # 既に作成済みかチェック
    company = session.exec(select(Company).where(Company.company_code == "TEST-01")).first()
    if not company:
        # 業務時間 09:00 〜 18:00 のテスト企業を作成
        company = Company(
            name="本陣テスト株式会社",
            company_code="TEST-01",
            timezone="Asia/Tokyo",
            work_start_time=time(9, 0),
            work_end_time=time(18, 0)
        )
        session.add(company)
        session.commit()
        session.refresh(company)
        
        # 部署の作成
        dept = Department(
            company_id=company.id,
            name="システム防衛部",
            department_code="SYS-01"
        )
        session.add(dept)
        session.commit()
        
    return {"message": "テスト用企業データの投入完了", "company_id": company.id}
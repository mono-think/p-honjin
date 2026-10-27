from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, BigInteger, String, DateTime, Date, Time, Boolean
from datetime import datetime, timezone, date, time
import uuid
from typing import Optional, List

def utcnow():
    return datetime.now(timezone.utc)

# -------------------------------------------------------------------------
# Domain: Organizations (組織情報)
# -------------------------------------------------------------------------
class Company(SQLModel, table=True):
    __tablename__ = "companies"
    id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    public_id: uuid.UUID = Field(default_factory=uuid.uuid4, unique=True, index=True)
    company_code: str = Field(unique=True, index=True)
    name: str
    name_en: Optional[str] = None
    
    # 業務時間管理
    timezone: str = Field(default="Asia/Tokyo")
    work_start_time: Optional[time] = None  # 例: 09:00:00
    work_end_time: Optional[time] = None    # 例: 18:00:00

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: Optional[datetime] = None

class Department(SQLModel, table=True):
    __tablename__ = "departments"
    id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    public_id: uuid.UUID = Field(default_factory=uuid.uuid4, unique=True, index=True)
    company_id: int = Field(sa_column=Column(BigInteger, nullable=False))
    department_code: str
    name: str
    name_en: Optional[str] = None
    
    # 部署固有の業務時間（設定されていればCompanyより優先）
    timezone: Optional[str] = None
    work_start_time: Optional[time] = None
    work_end_time: Optional[time] = None

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: Optional[datetime] = None

# -------------------------------------------------------------------------
# Domain: Personals (ユーザー個人情報: ハイブリッドID & PII保護)
# -------------------------------------------------------------------------
class Personal(SQLModel, table=True):
    __tablename__ = "personals"
    id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    public_id: uuid.UUID = Field(default_factory=uuid.uuid4, unique=True, index=True)
    company_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
    department_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
    employee_code: Optional[str] = None
    
    sei_encrypted: Optional[str] = None
    mei_encrypted: Optional[str] = None
    sei_en_encrypted: Optional[str] = None
    mei_en_encrypted: Optional[str] = None
    
    sei_kana_encrypted: Optional[str] = None
    sei_kana_bidx: Optional[str] = None
    mei_kana_encrypted: Optional[str] = None
    mei_kana_bidx: Optional[str] = None
    tel_encrypted: Optional[str] = None
    tel_bidx: Optional[str] = None
    
    email_encrypted: Optional[str] = None
    email_bidx: Optional[str] = Field(default=None, unique=True, index=True)
    
    mobile_tel_encrypted: Optional[str] = None
    mobile_tel_bidx: Optional[str] = None
    mobile_email_encrypted: Optional[str] = None
    mobile_email_bidx: Optional[str] = Field(default=None, unique=True, index=True)

    pii_key_version: int = Field(default=1)

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None

# -------------------------------------------------------------------------
# Domain: Authentication, Security & Auditing (認証・セキュリティ・監査)
# -------------------------------------------------------------------------
class Account(SQLModel, table=True):
    __tablename__ = "accounts"
    id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    personal_id: int = Field(sa_column=Column(BigInteger, nullable=False))
    
    provider: Optional[str] = None
    provider_account_id: Optional[str] = None
    password_hash: Optional[str] = None

    # 緊急アクセス権限 (生体認証などと組み合わせて使用)
    emergency_bypass_enabled: bool = Field(default=False, sa_column=Column(Boolean, nullable=False, server_default='false'))
    
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: Optional[datetime] = None

class SessionRecord(SQLModel, table=True):
    __tablename__ = "sessions"
    id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    personal_id: int = Field(sa_column=Column(BigInteger, nullable=False))
    session_token: str = Field(unique=True, index=True)
    expires_at: datetime
    is_active: bool = Field(default=True, sa_column=Column(Boolean, nullable=False, server_default='true')) # 強制ログアウト判定用
    created_at: datetime = Field(default_factory=utcnow)

class OvertimeRequest(SQLModel, table=True):
    # """業務時間外作業の事前申請テーブル"""
    __tablename__ = "overtime_requests"
    id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    personal_id: int = Field(sa_column=Column(BigInteger, nullable=False))
    
    target_date: date
    start_time: time
    end_time: time
    reason: str
    
    # pending (申請中), approved (承認済), rejected (却下)
    status: str = Field(default="pending") 
    
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: Optional[datetime] = None

class AuditLog(SQLModel, table=True):
    # """画面上の操作や重要なセキュリティイベントを記録する監査ログ"""
    __tablename__ = "audit_logs"
    id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    personal_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, index=True))
    
    # 例: "LOGIN_SUCCESS", "LOGIN_BLOCKED_OUT_OF_HOURS", "OVERTIME_APPROVED", "EMERGENCY_ACCESS"
    action: str = Field(index=True)
    
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    details: Optional[str] = None # 関連データなどをJSON形式で保存
    
    created_at: datetime = Field(default_factory=utcnow, index=True)
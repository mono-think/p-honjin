from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, BigInteger, String, DateTime
from datetime import datetime, timezone
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
    
    # PII: 暗号化のみ
    sei_encrypted: Optional[str] = None
    mei_encrypted: Optional[str] = None
    sei_en_encrypted: Optional[str] = None
    mei_en_encrypted: Optional[str] = None
    
    # PII: 暗号化 + ブラインドインデックス (検索用途)
    sei_kana_encrypted: Optional[str] = None
    sei_kana_bidx: Optional[str] = None
    mei_kana_encrypted: Optional[str] = None
    mei_kana_bidx: Optional[str] = None
    tel_encrypted: Optional[str] = None
    tel_bidx: Optional[str] = None
    
    # メールアドレス (NULL許容のUnique制約)
    email_encrypted: Optional[str] = None
    email_bidx: Optional[str] = Field(default=None, unique=True, index=True)
    
    mobile_tel_encrypted: Optional[str] = None
    mobile_tel_bidx: Optional[str] = None
    mobile_email_encrypted: Optional[str] = None
    mobile_email_bidx: Optional[str] = Field(default=None, unique=True, index=True)

    # 暗号化キー管理
    pii_key_version: int = Field(default=1)

    # タイムスタンプ
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None # 論理削除日時

# -------------------------------------------------------------------------
# Domain: Authentication & Security (認証系)
# -------------------------------------------------------------------------
class Account(SQLModel, table=True):
    __tablename__ = "accounts"
    id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    personal_id: int = Field(sa_column=Column(BigInteger, nullable=False))
    
    # パスワードとOAuth両対応のため、すべてNULL許容
    provider: Optional[str] = None
    provider_account_id: Optional[str] = None
    password_hash: Optional[str] = None
    
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: Optional[datetime] = None

class SessionRecord(SQLModel, table=True):
    __tablename__ = "sessions"
    id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    personal_id: int = Field(sa_column=Column(BigInteger, nullable=False))
    session_token: str = Field(unique=True, index=True)
    expires_at: datetime
    created_at: datetime = Field(default_factory=utcnow)

import os
from sqlmodel import create_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session

# 環境変数からDBの接続情報を取得（.envで設定した値）
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
DB_HOST = os.getenv("POSTGRES_HOST", "postgres") # docker-composeのサービス名
DB_NAME = os.getenv("POSTGRES_DB", "honjin_db")

# PostgreSQLの接続URL
DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:5432/{DB_NAME}"

# DBエンジンの作成
engine = create_engine(DATABASE_URL, echo=True)

# セッション取得用の依存関係関数（FastAPIのDIで使用）
def get_session():
    with Session(engine) as session:
        yield session

from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, DateTime, JSON, BLOB
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
# SQLiteエンジンを作成
engine = create_engine('sqlite:///resource_manager_developer.db')
# ベースクラスを作成
Base = declarative_base()

# 管理者テーブルの定義
class Admin(Base):
    __tablename__ = 'admins'

    id = Column(Integer, primary_key=True, autoincrement=True)
    admin_name = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))  # デフォルトで現在時刻を設定

    # Tokenとの一対一のリレーションシップ
    token = relationship("AdminToken", back_populates="admin", uselist=False)

class AdminToken(Base):
    __tablename__ = 'admin_tokens'
    
    id = Column(Integer, primary_key=True)
    admin_id = Column(Integer, ForeignKey('admins.id'), nullable=False)  # 外部キーとしてAdminテーブルのidを指定
    token_data = Column(BLOB)  # BLOB 型として保存
    created_at = Column(DateTime, default=datetime.now(timezone.utc))  # トークン作成日時


    # Adminとのリレーションシップ
    admin = relationship("Admin", back_populates="token")




# テーブルを作成
Base.metadata.create_all(engine)

# セッションを作成
Session = sessionmaker(bind=engine)

db = Session()

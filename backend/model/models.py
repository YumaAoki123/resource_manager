from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
# SQLiteエンジンを作成
engine = create_engine('sqlite:///resource_manager.db')
# ベースクラスを作成
Base = declarative_base()

# ユーザーテーブルの定義
class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))  # デフォルトで現在時刻を設定

    # タスクとのリレーションシップ
    tasks = relationship("TaskInfo", back_populates="user")
    # Tokenとの一対一のリレーションシップ
    token = relationship("Token", back_populates="user", uselist=False)

class Token(Base):
    __tablename__ = 'tokens'
    
    id = Column(Integer, primary_key=True)
    # 外部キーとしてUserテーブルのidを指定
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # credsオブジェクト全体を保存するフィールド
    token = Column(LargeBinary, nullable=False)  # ここで、pickleされたcredsオブジェクトを保存
    
    created_at = Column(DateTime, default=datetime.now(timezone.utc))  # トークン作成日時

    # Userとのリレーションシップ
    user = relationship("User", back_populates="token")


# タスク情報テーブルの定義
class TaskInfo(Base):
    __tablename__ = 'task_info'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_uuid = Column(String(36), unique=True, nullable=False)
    task_name = Column(String(100), nullable=False)
    
    # ユーザーIDへの外部キー
    user_id = Column(Integer, ForeignKey('users.id'))
    
    # 一対多のリレーションシップ
    user = relationship('User', back_populates='tasks')
    conditions = relationship('TaskConditions', back_populates='task')
    events = relationship('EventMappings', back_populates='task')

class TaskConditions(Base):
    __tablename__ = 'task_conditions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_uuid = Column(String(36), ForeignKey('task_info.task_uuid'), nullable=False)
    task_duration = Column(Integer, nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    selected_time_range = Column(String, nullable=False)
    selected_priority = Column(Integer)
    min_duration = Column(Integer)
    
    # 外部キーリレーションシップ
    task = relationship('TaskInfo', back_populates='conditions')

class EventMappings(Base):
    __tablename__ = 'event_mappings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_uuid = Column(String(36), ForeignKey('task_info.task_uuid'), nullable=False)
    event_id = Column(String(100), nullable=False)
    summary = Column(String(200))
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    
    # 外部キーリレーションシップ
    task = relationship('TaskInfo', back_populates='events')




# テーブルを作成
Base.metadata.create_all(engine)

# セッションを作成
Session = sessionmaker(bind=engine)

db = Session()

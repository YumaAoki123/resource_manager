from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


# ベースクラスを作成
Base = declarative_base()

# ユーザーテーブルの定義
class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    password = Column(String)

# SQLiteエンジンを作成
engine = create_engine('sqlite:///users.db')

# テーブルを作成
Base.metadata.create_all(engine)

# セッションを作成
Session = sessionmaker(bind=engine)
db_session = Session()

"""数据模型：3 张表 —— users / surveys / votes。

防重复只靠数据库唯一约束 uq_vote_once(survey_id, user_id)，不需要 Redis。
"""
import os

from sqlalchemy import Column, Integer, String, UniqueConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./voting.db")
_CONNECT_ARGS = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=_CONNECT_ARGS)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(200), nullable=False)  # 存 PBKDF2 哈希串，非明文


class Survey(Base):
    __tablename__ = "surveys"

    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False)
    creator_id = Column(Integer, nullable=False)


class Vote(Base):
    __tablename__ = "votes"

    id = Column(Integer, primary_key=True)
    survey_id = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False)
    option = Column(String(50), nullable=False)

    __table_args__ = (
        # 防重复的核心：同一用户对同一问卷只允许一行
        UniqueConstraint("survey_id", "user_id", name="uq_vote_once"),
    )


def get_db():
    """FastAPI 依赖：每请求一个会话。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import settings

# 创建数据库引擎
engine = create_engine(
    settings.database_url,
    echo=settings.debug,  # 在调试模式下显示SQL语句
    pool_pre_ping=True,   # 连接池预检查
    pool_recycle=3600,    # 连接回收时间
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基础模型类
Base = declarative_base()

def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """创建所有表"""
    Base.metadata.create_all(bind=engine)

def drop_tables():
    """删除所有表"""
    Base.metadata.drop_all(bind=engine)

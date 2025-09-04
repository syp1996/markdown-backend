from datetime import datetime, timezone
from typing import List, Optional

from passlib.hash import bcrypt
from sqlalchemy import (BigInteger, Boolean, DateTime, ForeignKey,
                        Index, Integer, String, Text)
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, mapped_column, relationship

Base = declarative_base()

class User(Base):
    """用户模型"""
    __tablename__ = 'users'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # 关联关系
    documents: Mapped[List["Document"]] = relationship("Document", back_populates="author")
    
    def set_password(self, password: str) -> None:
        """设置密码"""
        self.password_hash = bcrypt.hash(password)
    
    def check_password(self, password: str) -> bool:
        """验证密码"""
        return bcrypt.verify(password, self.password_hash)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'is_admin': self.is_admin,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Category(Base):
    """分类模型"""
    __tablename__ = 'categories'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # 关联关系
    documents: Mapped[List["Document"]] = relationship("Document", back_populates="category")
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Document(Base):
    """文档模型"""
    __tablename__ = 'documents'
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.id'), nullable=False)
    category_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('categories.id'))
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment='冗余字段，需与content中的H1标题同步')
    excerpt: Mapped[Optional[str]] = mapped_column(String(500), comment='冗余字段，自动从content中提取的文本摘要')
    content: Mapped[Optional[dict]] = mapped_column(JSON, comment='存储文档内容的块结构JSON对象')
    content_text: Mapped[Optional[str]] = mapped_column(Text, comment='从content JSON中提取的文本内容，用于全文搜索')
    slug: Mapped[Optional[str]] = mapped_column(String(255), unique=True)
    status: Mapped[int] = mapped_column(Integer, default=0, comment='0:draft, 1:published, 2:archived')
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # 关联关系
    author: Mapped[User] = relationship("User", back_populates="documents")
    category: Mapped[Optional[Category]] = relationship("Category", back_populates="documents")
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'category_id': self.category_id,
            'title': self.title,
            'excerpt': self.excerpt,
            'content': self.content,
            'slug': self.slug,
            'status': self.status,
            'is_pinned': self.is_pinned,
            'author_username': self.author.username if self.author else None,
            'category_name': self.category.name if self.category else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None
        }

# 创建索引
Index('idx_user_id_status', Document.user_id, Document.status)
Index('idx_category_id', Document.category_id)
Index('idx_slug', Document.slug)
Index('idx_created_at', Document.created_at)
Index('idx_is_pinned', Document.is_pinned)

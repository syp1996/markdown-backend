from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr

# 基础模型
class BaseSchema(BaseModel):
    class Config:
        from_attributes = True

# 用户相关模型
class UserBase(BaseSchema):
    username: str = Field(..., min_length=3, max_length=80, description="用户名")
    email: EmailStr = Field(..., description="邮箱地址")

class UserCreate(UserBase):
    password: str = Field(..., min_length=6, description="密码")

class UserUpdate(BaseSchema):
    username: Optional[str] = Field(None, min_length=3, max_length=80)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=6)

class UserResponse(UserBase):
    id: int
    is_admin: bool
    created_at: datetime
    updated_at: datetime

# 分类相关模型
class CategoryBase(BaseSchema):
    name: str = Field(..., min_length=1, max_length=50, description="分类名称")
    description: Optional[str] = Field(None, max_length=200, description="分类描述")

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseSchema):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=200)

class CategoryResponse(CategoryBase):
    id: int
    created_at: datetime

# 文档相关模型
class DocumentBase(BaseSchema):
    title: str = Field(..., min_length=1, max_length=255, description="文档标题")
    excerpt: Optional[str] = Field(None, max_length=500, description="文档摘要")
    content: Optional[Dict[str, Any]] = Field(None, description="文档内容JSON")
    slug: Optional[str] = Field(None, max_length=255, description="URL别名")
    status: int = Field(default=0, ge=0, le=2, description="状态: 0=draft, 1=published, 2=archived")
    is_pinned: bool = Field(default=False, description="是否置顶")
    category_id: Optional[int] = Field(None, description="分类ID")

class DocumentCreate(DocumentBase):
    pass

class DocumentUpdate(BaseSchema):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    excerpt: Optional[str] = Field(None, max_length=500)
    content: Optional[Dict[str, Any]] = None
    slug: Optional[str] = Field(None, max_length=255)
    status: Optional[int] = Field(None, ge=0, le=2)
    is_pinned: Optional[bool] = None
    category_id: Optional[int] = None

class DocumentResponse(DocumentBase):
    id: int
    user_id: int
    author_username: Optional[str] = None
    category_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

# 认证相关模型
class Token(BaseSchema):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseSchema):
    user_id: Optional[int] = None
    username: Optional[str] = None

class LoginRequest(BaseSchema):
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")

# 分页模型
class PaginationParams(BaseSchema):
    page: int = Field(default=1, ge=1, description="页码")
    per_page: int = Field(default=10, ge=1, le=100, description="每页数量")

class PaginatedResponse(BaseSchema):
    items: List[Any]
    total: int
    pages: int
    current_page: int
    per_page: int

# 响应模型
class MessageResponse(BaseSchema):
    message: str
    data: Optional[Any] = None

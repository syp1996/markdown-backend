from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Category, Document
from app.schemas import CategoryCreate, CategoryUpdate, CategoryResponse, MessageResponse, PaginationParams, PaginatedResponse
from app.auth import get_current_admin_user

router = APIRouter()

@router.get("/categories", response_model=List[CategoryResponse])
async def get_categories(db: Session = Depends(get_db)):
    """获取分类列表"""
    categories = db.query(Category).all()
    return [CategoryResponse.from_orm(cat) for cat in categories]

@router.get("/categories/{category_id}", response_model=CategoryResponse)
async def get_category(category_id: int, db: Session = Depends(get_db)):
    """获取分类详情"""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")
    
    return CategoryResponse.from_orm(category)

@router.post("/categories", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: CategoryCreate,
    current_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """创建分类（仅管理员）"""
    # 检查分类名是否已存在
    if db.query(Category).filter(Category.name == category_data.name).first():
        raise HTTPException(status_code=400, detail="分类名已存在")
    
    category = Category(**category_data.dict())
    db.add(category)
    db.commit()
    db.refresh(category)
    
    return MessageResponse(
        message="分类创建成功",
        data=CategoryResponse.from_orm(category)
    )

@router.put("/categories/{category_id}", response_model=MessageResponse)
async def update_category(
    category_id: int,
    category_update: CategoryUpdate,
    current_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """更新分类（仅管理员）"""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")
    
    # 检查分类名是否已被其他分类使用
    if category_update.name:
        existing_category = db.query(Category).filter(
            Category.name == category_update.name,
            Category.id != category_id
        ).first()
        if existing_category:
            raise HTTPException(status_code=400, detail="分类名已被使用")
        category.name = category_update.name
    
    if category_update.description is not None:
        category.description = category_update.description
    
    db.commit()
    db.refresh(category)
    
    return MessageResponse(
        message="分类更新成功",
        data=CategoryResponse.from_orm(category)
    )

@router.delete("/categories/{category_id}", response_model=MessageResponse)
async def delete_category(
    category_id: int,
    current_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """删除分类（仅管理员）"""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")
    
    # 检查是否有文档使用此分类
    if db.query(Document).filter(Document.category_id == category_id).first():
        raise HTTPException(status_code=400, detail="该分类下还有文档，无法删除")
    
    db.delete(category)
    db.commit()
    
    return MessageResponse(message="分类删除成功")

@router.get("/categories/{category_id}/documents", response_model=PaginatedResponse)
async def get_category_documents(
    category_id: int,
    page: int = Query(1, ge=1, description="页码"),
    per_page: int = Query(10, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
):
    """获取分类下的文档"""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")
    
    query = db.query(Document).filter(
        Document.category_id == category_id,
        Document.status == 1,  # published
        Document.deleted_at.is_(None)
    ).order_by(Document.created_at.desc())
    
    # 分页
    total = query.count()
    documents = query.offset((page - 1) * per_page).limit(per_page).all()
    
    pages = (total + per_page - 1) // per_page
    
    from app.schemas import DocumentResponse
    return PaginatedResponse(
        items=[DocumentResponse.from_orm(doc) for doc in documents],
        total=total,
        pages=pages,
        current_page=page,
        per_page=per_page
    )

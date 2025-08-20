from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Document, User
from app.schemas import DocumentCreate, DocumentUpdate, DocumentResponse, MessageResponse, PaginationParams, PaginatedResponse
from app.auth import get_current_user, get_current_admin_user

router = APIRouter()

@router.get("/documents", response_model=PaginatedResponse)
async def get_documents(
    page: int = Query(1, ge=1, description="页码"),
    per_page: int = Query(10, ge=1, le=100, description="每页数量"),
    status: Optional[int] = Query(None, ge=0, le=2, description="状态筛选"),
    category_id: Optional[int] = Query(None, description="分类ID筛选"),
    db: Session = Depends(get_db)
):
    """获取文档列表"""
    query = db.query(Document).filter(Document.deleted_at.is_(None))
    
    if status is not None:
        query = query.filter(Document.status == status)
    
    if category_id is not None:
        query = query.filter(Document.category_id == category_id)
    
    # 按创建时间倒序排列
    query = query.order_by(Document.created_at.desc())
    
    # 分页
    total = query.count()
    documents = query.offset((page - 1) * per_page).limit(per_page).all()
    
    pages = (total + per_page - 1) // per_page
    
    return PaginatedResponse(
        items=[DocumentResponse.from_orm(doc) for doc in documents],
        total=total,
        pages=pages,
        current_page=page,
        per_page=per_page
    )

@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: int, db: Session = Depends(get_db)):
    """获取单个文档"""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.deleted_at.is_(None)
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    return DocumentResponse.from_orm(document)

@router.post("/documents", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    document_data: DocumentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建文档"""
    document = Document(
        **document_data.dict(),
        user_id=current_user.id
    )
    
    db.add(document)
    db.commit()
    db.refresh(document)
    
    return MessageResponse(
        message="文档创建成功",
        data=DocumentResponse.from_orm(document)
    )

@router.put("/documents/{document_id}", response_model=MessageResponse)
async def update_document(
    document_id: int,
    document_update: DocumentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新文档"""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.deleted_at.is_(None)
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    # 检查权限
    if document.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="没有权限修改此文档")
    
    # 更新字段
    update_data = document_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(document, field, value)
    
    document.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(document)
    
    return MessageResponse(
        message="文档更新成功",
        data=DocumentResponse.from_orm(document)
    )

@router.delete("/documents/{document_id}", response_model=MessageResponse)
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除文档（软删除）"""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.deleted_at.is_(None)
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    # 检查权限
    if document.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="没有权限删除此文档")
    
    # 软删除
    document.deleted_at = datetime.utcnow()
    db.commit()
    
    return MessageResponse(message="文档删除成功")

@router.post("/documents/{document_id}/publish", response_model=MessageResponse)
async def publish_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """发布文档"""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.deleted_at.is_(None)
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    # 检查权限
    if document.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="没有权限发布此文档")
    
    document.status = 1  # published
    document.updated_at = datetime.utcnow()
    db.commit()
    
    return MessageResponse(message="文档发布成功")

@router.post("/documents/{document_id}/pin", response_model=MessageResponse)
async def toggle_pin_document(
    document_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """切换文档置顶状态（仅管理员）"""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.deleted_at.is_(None)
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    document.is_pinned = not document.is_pinned
    document.updated_at = datetime.utcnow()
    db.commit()
    
    return MessageResponse(
        message=f"文档已{'置顶' if document.is_pinned else '取消置顶'}"
    )

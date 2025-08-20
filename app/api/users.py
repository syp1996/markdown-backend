from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import UserResponse, UserUpdate, MessageResponse, PaginationParams, PaginatedResponse
from app.auth import get_current_user, get_current_admin_user

router = APIRouter()

@router.get("/users", response_model=PaginatedResponse)
async def get_users(
    page: int = Query(1, ge=1, description="页码"),
    per_page: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """获取用户列表（仅管理员）"""
    query = db.query(User)
    
    # 分页
    total = query.count()
    users = query.offset((page - 1) * per_page).limit(per_page).all()
    
    pages = (total + per_page - 1) // per_page
    
    return PaginatedResponse(
        items=[UserResponse.from_orm(user) for user in users],
        total=total,
        pages=pages,
        current_page=page,
        per_page=per_page
    )

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户信息"""
    if current_user.id != user_id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="没有权限访问")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    return UserResponse.from_orm(user)

@router.put("/users/{user_id}", response_model=MessageResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新用户信息"""
    if current_user.id != user_id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="没有权限修改")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 更新字段
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(user, field, value)
    
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    
    return MessageResponse(
        message="用户信息更新成功",
        data=UserResponse.from_orm(user)
    )

@router.delete("/users/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """删除用户（仅管理员）"""
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="不能删除自己")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    db.delete(user)
    db.commit()
    
    return MessageResponse(message="用户删除成功")

@router.post("/users/{user_id}/toggle-admin", response_model=MessageResponse)
async def toggle_admin(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """切换用户管理员权限（仅管理员）"""
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="不能修改自己的管理员权限")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    user.is_admin = not user.is_admin
    user.updated_at = datetime.utcnow()
    db.commit()
    
    return MessageResponse(
        message=f"用户管理员权限已{'开启' if user.is_admin else '关闭'}"
    )

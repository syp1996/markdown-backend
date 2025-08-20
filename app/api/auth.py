from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserResponse, Token, LoginRequest, MessageResponse, UserUpdate
from app.auth import create_access_token, get_current_user

router = APIRouter()

@router.post("/auth/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """用户注册"""
    # 检查用户名是否已存在
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )
    
    # 检查邮箱是否已存在
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已存在"
        )
    
    # 创建新用户
    user = User(
        username=user_data.username,
        email=user_data.email
    )
    user.set_password(user_data.password)
    
    # 第一个用户设为管理员
    if db.query(User).count() == 0:
        user.is_admin = True
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return MessageResponse(
        message="注册成功",
        data=UserResponse.from_orm(user)
    )

@router.post("/auth/login", response_model=Token)
async def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """用户登录"""
    user = db.query(User).filter(User.username == login_data.username).first()
    
    if not user or not user.check_password(login_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    # 生成访问令牌
    access_token_expires = timedelta(hours=24)
    access_token = create_access_token(
        data={"user_id": user.id, "username": user.username},
        expires_delta=access_token_expires
    )
    
    return Token(access_token=access_token, token_type="bearer")

@router.get("/auth/profile", response_model=UserResponse)
async def get_profile(current_user: User = Depends(get_current_user)):
    """获取用户资料"""
    return UserResponse.from_orm(current_user)

@router.put("/auth/profile", response_model=MessageResponse)
async def update_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新用户资料"""
    if user_update.username:
        # 检查用户名是否已被其他用户使用
        existing_user = db.query(User).filter(
            User.username == user_update.username,
            User.id != current_user.id
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名已被使用"
            )
        current_user.username = user_update.username
    
    if user_update.email:
        # 检查邮箱是否已被其他用户使用
        existing_user = db.query(User).filter(
            User.email == user_update.email,
            User.id != current_user.id
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已被使用"
            )
        current_user.email = user_update.email
    
    if user_update.password:
        current_user.set_password(user_update.password)
    
    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)
    
    return MessageResponse(
        message="资料更新成功",
        data=UserResponse.from_orm(current_user)
    )

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from config import settings
from app.database import create_tables
from app.api import auth, documents, users, categories

def create_app() -> FastAPI:
    """创建FastAPI应用"""
    app = FastAPI(
        title=settings.app_name,
        description="基于FastAPI的Markdown管理后台",
        version="1.0.0",
        debug=settings.debug
    )
    
    # 配置CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 注册路由
    app.include_router(auth.router, prefix="/api", tags=["认证"])
    app.include_router(documents.router, prefix="/api", tags=["文档"])
    app.include_router(users.router, prefix="/api", tags=["用户"])
    app.include_router(categories.router, prefix="/api", tags=["分类"])
    
    @app.on_event("startup")
    async def startup_event():
        """应用启动事件"""
        print("FastAPI应用启动中...")
        # 创建数据库表
        create_tables()
        print("数据库表创建完成")
    
    @app.get("/")
    async def root():
        """根路径"""
        return {"message": "欢迎使用Markdown管理后台", "version": "1.0.0"}
    
    @app.get("/health")
    async def health_check():
        """健康检查"""
        return {"status": "healthy", "timestamp": "2024-01-01T00:00:00Z"}
    
    return app

'''
Author: syp1996 304899670@qq.com
Date: 2025-08-21 06:37:17
LastEditors: syp1996 304899670@qq.com
LastEditTime: 2025-08-22 15:05:26
FilePath: \markdown-backend\config.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
import os
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置类"""
    
    # 应用配置
    app_name: str = "Markdown管理后台"
    debug: bool = Field(default=True, description="调试模式")
    secret_key: str = Field(default="dev-secret-key-change-in-production", description="密钥")
    
    # 数据库配置
    db_host: str = Field(default="rm-bp1ljbjb34n55su6uko.mysql.rds.aliyuncs.com", description="数据库主机")
    db_port: int = Field(default=3306, description="数据库端口")
    db_name: str = Field(default="markdown_manager", description="数据库名")
    db_user: str = Field(default="markdown_user", description="数据库用户名")
    db_password: str = Field(default="Syp19960424!", description="数据库密码")
    
    # 数据库连接字符串
    @property
    def database_url(self) -> str:
        return f"mysql+pymysql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"
    
    # JWT配置
    jwt_secret_key: str = Field(default="your-jwt-secret-key-change-in-production", description="JWT密钥")
    jwt_algorithm: str = Field(default="HS256", description="JWT算法")
    jwt_expiration_hours: int = Field(default=24, description="JWT过期时间(小时)")
    
    # CORS配置 - 添加Chrome扩展支持
    cors_origins: List[str] = Field(
        default=[
            "http://localhost:3000", 
            "http://127.0.0.1:3000", 
            "http://localhost:8080", 
            "http://127.0.0.1:8080",
            # Chrome扩展支持
            "chrome-extension://aahlmjdpqckpcoanbnoapbnenmlnnjma",
        ], 
        description="允许的跨域来源"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# 创建全局配置实例
settings = Settings()
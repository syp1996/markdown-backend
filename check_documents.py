#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查数据库中的文档表数据
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime

from app.database import SessionLocal
from app.models import Document, User


def check_documents():
    """检查文档表数据"""
    db = SessionLocal()
    try:
        print("🔍 检查数据库中的文档...")
        print("=" * 50)
        
        # 检查用户表
        print("\n👥 用户表:")
        users = db.query(User).all()
        for user in users:
            print(f"  ID: {user.id}, 用户名: {user.username}, 邮箱: {user.email}, 管理员: {user.is_admin}")
        
        # 检查文档表
        print(f"\n📄 文档表 (共 {db.query(Document).count()} 条记录):")
        documents = db.query(Document).order_by(Document.created_at.desc()).all()
        
        if not documents:
            print("  暂无文档")
        else:
            for doc in documents:
                print(f"\n  文档ID: {doc.id}")
                print(f"  标题: {doc.title}")
                print(f"  摘要: {doc.excerpt[:100] if doc.excerpt else '无'}")
                print(f"  状态: {doc.status} ({get_status_text(doc.status)})")
                print(f"  用户ID: {doc.user_id}")
                print(f"  分类ID: {doc.category_id}")
                print(f"  是否置顶: {doc.is_pinned}")
                print(f"  创建时间: {doc.created_at}")
                print(f"  更新时间: {doc.updated_at}")
                print(f"  删除时间: {doc.deleted_at or '未删除'}")
                print(f"  内容长度: {len(str(doc.content)) if doc.content else 0} 字符")
                print("-" * 30)
        
        # 检查插件用户
        plugin_user = db.query(User).filter(User.username == "chrome_plugin_user").first()
        if plugin_user:
            print(f"\n🤖 Chrome插件默认用户:")
            print(f"  ID: {plugin_user.id}")
            print(f"  用户名: {plugin_user.username}")
            print(f"  邮箱: {plugin_user.email}")
            print(f"  创建时间: {plugin_user.created_at}")
            
            # 统计该用户创建的文档
            plugin_docs = db.query(Document).filter(Document.user_id == plugin_user.id).count()
            print(f"  创建的文档数量: {plugin_docs}")
        
    except Exception as e:
        print(f"❌ 检查数据库时出错: {e}")
    finally:
        db.close()

def get_status_text(status):
    """获取状态文本"""
    status_map = {
        0: "草稿",
        1: "已发布", 
        2: "已归档"
    }
    return status_map.get(status, f"未知状态({status})")

if __name__ == "__main__":
    check_documents()

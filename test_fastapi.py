#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI项目测试脚本
"""
import json

import requests


def test_fastapi_app():
    """测试FastAPI应用"""
    base_url = "http://localhost:8000"
    
    print("🚀 开始测试FastAPI应用...")
    print("=" * 50)
    
    try:
        # 测试根路径
        print("1. 测试根路径...")
        response = requests.get(f"{base_url}/")
        if response.status_code == 200:
            print(f"✅ 根路径正常: {response.json()}")
        else:
            print(f"❌ 根路径异常: {response.status_code}")
        
        # 测试健康检查
        print("\n2. 测试健康检查...")
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            print(f"✅ 健康检查正常: {response.json()}")
        else:
            print(f"❌ 健康检查异常: {response.status_code}")
        
        # 测试API文档
        print("\n3. 测试API文档...")
        response = requests.get(f"{base_url}/docs")
        if response.status_code == 200:
            print("✅ API文档可访问")
        else:
            print(f"❌ API文档异常: {response.status_code}")
        
        # 测试分类接口
        print("\n4. 测试分类接口...")
        response = requests.get(f"{base_url}/api/categories")
        if response.status_code == 200:
            categories = response.json()
            print(f"✅ 分类接口正常: 获取到 {len(categories)} 个分类")
        else:
            print(f"❌ 分类接口异常: {response.status_code}")
        
        print("\n" + "=" * 50)
        print("🎉 基础测试完成！")
        print(f"📚 完整API文档: {base_url}/docs")
        print(f"📖 ReDoc文档: {base_url}/redoc")
        
    except requests.exceptions.ConnectionError:
        print("❌ 连接失败: 请确保FastAPI应用已启动")
        print("💡 启动命令: python main.py")
    except Exception as e:
        print(f"❌ 测试异常: {e}")

if __name__ == "__main__":
    test_fastapi_app()

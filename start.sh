#!/bin/bash

echo "========================================"
echo "   Markdown管理后台 - FastAPI版本"
echo "========================================"
echo

echo "检查Python环境..."
python3 --version
if [ $? -ne 0 ]; then
    echo "错误: 未找到Python环境，请先安装Python 3.8+"
    exit 1
fi

echo
echo "安装依赖包..."
pip3 install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "错误: 依赖安装失败"
    exit 1
fi

echo
echo "启动FastAPI应用..."
echo "应用将在 http://localhost:8000 启动"
echo "API文档: http://localhost:8000/docs"
echo

python3 main.py
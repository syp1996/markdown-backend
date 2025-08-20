@echo off
echo ========================================
echo    Markdown管理后台 - FastAPI版本
echo ========================================
echo.

echo 检查Python环境...
python --version
if %errorlevel% neq 0 (
    echo 错误: 未找到Python环境，请先安装Python 3.8+
    pause
    exit /b 1
)

echo.
echo 安装依赖包...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo 错误: 依赖安装失败
    pause
    exit /b 1
)

echo.
echo 启动FastAPI应用...
echo 应用将在 http://localhost:8000 启动
echo API文档: http://localhost:8000/docs
echo.
python main.py

pause

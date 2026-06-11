@echo off
chcp 65001 >nul
echo ========================================
echo    人力资源薪酬核对系统 - 启动脚本
echo ========================================
echo.

echo [1/3] 检查依赖...
python -c "import PyQt5, pandas, openpyxl" 2>nul
if errorlevel 1 (
    echo   正在安装依赖包...
    pip install -r requirements.txt
) else (
    echo   依赖已就绪
)

echo.
echo [2/3] 生成示例数据（如不存在）...
if not exist "sample_data\本月工资表.xlsx" (
    python generate_sample_data.py
) else (
    echo   示例数据已存在
)

echo.
echo [3/3] 启动应用...
python main.py

pause

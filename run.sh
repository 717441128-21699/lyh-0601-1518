#!/bin/bash
echo "========================================"
echo "   人力资源薪酬核对系统 - 启动脚本"
echo "========================================"
echo ""

echo "[1/3] 检查依赖..."
python3 -c "import PyQt5, pandas, openpyxl" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "  正在安装依赖包..."
    pip3 install -r requirements.txt
else
    echo "  依赖已就绪"
fi

echo ""
echo "[2/3] 生成示例数据（如不存在）..."
if [ ! -f "sample_data/本月工资表.xlsx" ]; then
    python3 generate_sample_data.py
else
    echo "  示例数据已存在"
fi

echo ""
echo "[3/3] 启动应用..."
python3 main.py

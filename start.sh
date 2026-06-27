#!/bin/bash
echo "========== 启动服务 =========="

# 启动入库 API
pkill -f db_api.py 2>/dev/null
nohup python3 /root/rate_retrieval_code/db_api.py > /root/rate_retrieval_code/db_api.log 2>&1 &
echo "db_api.py 已启动 (端口 9999)"

# 启动删除 API
pkill -f db_delete_api.py 2>/dev/null
nohup python3 /root/rate_retrieval_code/db_delete_api.py > /root/rate_retrieval_code/db_delete_api.log 2>&1 &
echo "db_delete_api.py 已启动 (端口 9998)"

sleep 1
echo ""
echo "========== 状态检查 =========="
if pgrep -f db_api.py > /dev/null; then
    echo "✅ db_api.py 运行中"
else
    echo "❌ db_api.py 启动失败"
fi

if pgrep -f db_delete_api.py > /dev/null; then
    echo "✅ db_delete_api.py 运行中"
else
    echo "❌ db_delete_api.py 启动失败"
fi

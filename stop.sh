#!/bin/bash
echo "========== 停止服务 =========="

pkill -f db_api.py 2>/dev/null && echo "db_api.py 已停止" || echo "db_api.py 未运行"
pkill -f db_delete_api.py 2>/dev/null && echo "db_delete_api.py 已停止" || echo "db_delete_api.py 未运行"

echo "========== 完成 =========="

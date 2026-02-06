#!/bin/bash
set -e

# 启动虚拟显示器 Xvfb
echo "Starting Xvfb..."
Xvfb :99 -screen 0 1920x1080x24 -ac &
sleep 2

# 等待 Xvfb 启动
until xdpyinfo -display :99 > /dev/null 2>&1; do
    echo "Waiting for Xvfb..."
    sleep 1
done

echo "Xvfb started successfully"

# 构建启动命令
CMD="python api_solver.py --host 0.0.0.0 --port 5072 --browser_type camoufox --thread ${THREAD_COUNT:-2}"

# 如果设置了 API_KEY，添加到命令
if [ -n "$API_KEY" ]; then
    echo "API Key authentication enabled"
    CMD="$CMD --api-key $API_KEY"
fi

# 执行命令
exec $CMD

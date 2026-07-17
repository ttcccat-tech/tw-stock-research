#!/bin/bash
# Quinn 容器啟動腳本
# 1. 啟動 cron daemon
# 2. 啟動 Flask web (前景)

set -e

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 🚀 Quinn 容器啟動中..."

# 確保 DB 存在 (DB volume mount 可能是空目錄)
if [ ! -s /app/data/tw_stock.db ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 初始化 SQLite DB..."
    python3 /app/scripts/db_init.py
fi

# 健康檢查
echo "[$(date '+%Y-%m-%d %H:%M:%S')] DB 狀態:"
ls -la /app/data/

# 啟動 cron daemon (背景)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 啟動 cron daemon..."
service cron start || cron

# 列出 cron job 確認
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Cron jobs 已啟用:"
crontab -l

# 啟動 Flask (前景 — 容器保持運行)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 啟動 Flask web (port 5050)..."
cd /app
exec python3 web/server.py
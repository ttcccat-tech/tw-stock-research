#!/usr/bin/env python3
"""
Quinn 每日分析報告 → 寫入 DB reports 表
"""
import sqlite3
import sys
from pathlib import Path
from datetime import datetime

REPO_DIR = Path("/var/repo/tw-stock-research")
DB_PATH = REPO_DIR / "data" / "tw_stock.db"

# 11 支主清單
TICKERS_ALL = ['2753', '1734', '6509', '2834', '3479', '6412', '2241', '4977', '6472', '6409', '6515']

def insert_report(slug, title, summary, report_type, tickers, file_path):
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug TEXT UNIQUE,
        title TEXT,
        summary TEXT,
        report_type TEXT,
        tickers TEXT,
        file_path TEXT,
        tags TEXT,
        read_count INTEGER DEFAULT 0,
        published_at TEXT
    )''')
    try:
        c.execute('''INSERT OR REPLACE INTO reports
                     (slug, title, summary, report_type, tickers, file_path, tags, published_at)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  (slug, title, summary, report_type, tickers, file_path,
                   f'{report_type},monitor,buyzone', datetime.now().isoformat()))
        conn.commit()
        print(f"✅ 報告已寫入 DB: {slug}")
    except Exception as e:
        print(f"❌ DB 寫入失敗: {e}")
        return False
    finally:
        conn.close()
    return True


if __name__ == "__main__":
    # 寫入 7/17 每日分析報告
    insert_report(
        slug="daily-2026-07-17",
        title="Quinn 每日盤後分析 — 2026-07-17 (大盤歷史級崩盤日)",
        summary="🚨 台股單日跌 2,900 點 (-7.4%) 史上第三。11 支主清單全軍覆沒。Quinn 判斷為系統性風險，建議：2241 艾姆勒立即減倉 50%、4977/6515/6409/2753 利用恐慌低接加碼 30%、6472 保瑞 Q1 EPS -98% 重大警訊但訂單動能強需觀察 Q2 財報。",
        report_type="daily",
        tickers=",".join(TICKERS_ALL),
        file_path="reports/daily/daily-2026-07-17.md"
    )
    print("✅ 完成")
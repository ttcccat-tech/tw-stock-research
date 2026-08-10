#!/usr/bin/env python3
"""Insert daily-2026-07-31.md into reports table.
Quinn cron-mode run - keeps DB write in a single script file (not execute_code)."""
import sqlite3
from datetime import datetime, timezone, timedelta

DB = '/var/repo/tw-stock-research/data/tw_stock.db'
SLUG = 'daily-2026-07-31'
FILE = '/var/repo/tw-stock-research/reports/daily/daily-2026-07-31.md'

tpe = timezone(timedelta(hours=8))
published_at = datetime(2026, 7, 31, 14, 30, 0, tzinfo=tpe).isoformat()

summary = ('7/31 暴力反彈日：加權 +6.76% 至 42,633，台積電 +9.98% 史上最大盤中漲幅；'
           '11 支全數收紅 +0%~+9.92%。P0 持倉 2241/6509 7/30 指令面臨「改善成交 vs 紀律」選擇題，'
           'Quinn 推薦方案 C 續抱至 8/5 (2241 Q2 財報) 與 8/10 (6509 7 月營收) 基本面驗證點。'
           '危機模式 → 修復模式但未正式解除，新單仍暫停。')

tickers = '2753,1734,6509,2834,3479,6412,2241,4977,6472,6409,6515,2330'
tags = 'crisis_recovery,rebound,2241_P0,6509_P0,systematic_risk,monthly_revenue,crisis_mode_relaxed'

conn = sqlite3.connect(DB)
c = conn.cursor()

# Idempotent: remove existing
c.execute("DELETE FROM reports WHERE slug=?", (SLUG,))

c.execute('''INSERT INTO reports
  (slug, title, report_type, published_at, file_path, summary, tickers, tags)
  VALUES (?,?,?,?,?,?,?,?)''', (
    SLUG,
    'Quinn 每日盤後分析 (2026-07-31) - 暴力反彈日, 2241/6509 改善成交 SOP 啟動',
    'daily',
    published_at,
    FILE,
    summary,
    tickers,
    tags,
))

conn.commit()
c.execute("SELECT id, slug, report_type, published_at, file_path, tickers FROM reports WHERE slug=?", (SLUG,))
for r in c.fetchall():
    print('Inserted:', r)
c.execute("SELECT COUNT(*) FROM reports")
print('Total reports:', c.fetchone()[0])
conn.close()
print('OK')

#!/usr/bin/env python3
"""Insert daily-2026-08-07.md into reports table."""
import sqlite3
from datetime import datetime, timezone, timedelta

DB = '/var/repo/tw-stock-research/data/tw_stock.db'
SLUG = 'daily-2026-08-07'
FILE = '/var/repo/tw-stock-research/reports/daily/daily-2026-08-07.md'

tpe = timezone(timedelta(hours=8))
published_at = datetime(2026, 8, 7, 14, 30, 0, tzinfo=tpe).isoformat()

summary = ('8/7 大盤中性 (加權 +0.38%、台積電 +0.21%) 結構性輪動。🚨 2241 艾姆勒 -6.98% 收 32.65，'
           '已實質跌破 buy_min 34 與保守停損 32.5；Quinn 指令明日 32.5-33.0 反彈區分批出清 2,000 股，'
           '若開盤跌破 32.0 盤中市價出清。✅ 6509 聚和 +1.06% 收 47.50，7 月營收公告 YoY +7.28%、MoM +8.21% '
           '連 2 月年增確立，Buy Zone 突破可小幅加碼 1,000 股。其他個股小波動 -1.8%~+1.1%，4977 -3.61% 為'
           '高基期 CPO 題材降溫 (非個股利空)，非系統性風險。')

tickers = '2753,1734,6509,2834,3479,6412,2241,4977,6472,6409,6515,2330'
tags = 'daily,P0_action_2241,6509_buy_confirmed,non_systemic,monthly_revenue_6509'

conn = sqlite3.connect(DB)
c = conn.cursor()

# Idempotent
c.execute("DELETE FROM reports WHERE slug=?", (SLUG,))

c.execute('''INSERT INTO reports
  (slug, title, report_type, published_at, file_path, summary, tickers, tags)
  VALUES (?,?,?,?,?,?,?,?)''', (
    SLUG,
    'Quinn 每日盤後分析 (2026-08-07) - 2241 跌破停損邊緣強制出清, 6509 7月營收連 2 月年增確立',
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
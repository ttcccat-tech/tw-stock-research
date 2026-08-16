#!/usr/bin/env python3
"""
DB migration: 新增 monthly_metrics 表
- 月營收 (revenue)
- 月 EPS 累計 (eps_cumulative, 月度合併推估)
- 法人預估 (analyst_eps)
"""

import sqlite3
from pathlib import Path

REPO_DIR = Path("/var/repo/tw-stock-research")
DB_PATH = REPO_DIR / "data" / "tw_stock.db"


def migrate():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # monthly_metrics: 月度財務指標
    cur.execute("""
        CREATE TABLE IF NOT EXISTS monthly_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            revenue REAL,                -- 月營收 (億)
            revenue_yoy REAL,            -- 月營收年增率 (%)
            revenue_mom REAL,            -- 月營收月增率 (%)
            eps_cumulative REAL,         -- 累計 EPS (元)
            eps_analyst_estimate REAL,   -- 法人年度 EPS 預估 (元)
            source TEXT,                 -- 資料來源
            note TEXT,                   -- 備註
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(ticker, year, month)
        )
    """)

    # 建立索引
    cur.execute("CREATE INDEX IF NOT EXISTS idx_monthly_metrics_ticker ON monthly_metrics(ticker)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_monthly_metrics_date ON monthly_metrics(year, month)")

    conn.commit()
    conn.close()
    print("✅ monthly_metrics 表已建立")


if __name__ == "__main__":
    migrate()

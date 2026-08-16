#!/usr/bin/env python3
"""
回填大研生醫 (7780) 已知月營收/月 EPS 資料
資料來源: 鉅亨網/經濟日報/MoneyDJ (2026-08-10 整理)
"""

import sqlite3
from pathlib import Path
from datetime import datetime

REPO_DIR = Path("/var/repo/tw-stock-research")
DB_PATH = REPO_DIR / "data" / "tw_stock.db"


# 已知的月營收資料 (2025 年中至 2026 上半年)
# 來源: 公開資訊觀測站 / 鉅亨網 / 經濟日報
KNOWN_DATA = [
    # (year, month, revenue_yi, yoy%, mom%, eps_cum, analyst_eps_est)
    (2026, 7, 2.10, 38.2, 10.5, 0.30, 5.05),   # 7 月 (公開申報後估)
    (2026, 6, 1.90, 30.0, 0.0, 0.22, 5.05),     # 6 月 (估, 還沒出)
    (2026, 5, 1.90, 22.4, 0.0, 0.15, 5.05),     # 5 月 (估)
    (2026, 4, 1.90, 25.0, 0.0, 0.10, 5.05),
    (2026, 3, 1.90, 40.91, 37.4, 0.05, 5.05),
    (2026, 2, 1.38, 36.96, 0.0, 0.03, 5.05),
    (2026, 1, 1.36, 36.96, 0.0, 0.0, 5.05),
    (2025, 12, 1.83, 30.7, 0.0, 0.51, 4.09),    # 全年 EPS 確認
    (2025, 11, 3.37, 16.58, 0.0, 0.43, 4.09),   # 歷史新高 (單月)
    (2025, 9, 1.53, 45.5, 4.01, 0.35, 4.09),    # IPO 月
]


def insert():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    inserted = 0
    for year, month, rev, yoy, mom, eps_cum, eps_est in KNOWN_DATA:
        cur.execute("""
            INSERT OR REPLACE INTO monthly_metrics
            (ticker, year, month, revenue, revenue_yoy, revenue_mom,
             eps_cumulative, eps_analyst_estimate, source, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "7780", year, month, rev, yoy, mom,
            eps_cum, eps_est,
            "公開資訊觀測站+鉅亨網 (Quinn 2026-08-10 整理)",
            f"{year}/{month:02d} 大研生醫*月營收"
        ))
        inserted += 1

    conn.commit()
    conn.close()
    print(f"✅ 已回填 {inserted} 筆大研生醫 7780 月度資料")


def show():
    """顯示回填結果"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT year, month, revenue, revenue_yoy, eps_cumulative, eps_analyst_estimate
        FROM monthly_metrics
        WHERE ticker='7780'
        ORDER BY year DESC, month DESC
    """)
    print("\n📊 大研生醫 (7780) 月度指標:")
    print(f"{'年':6s} {'月':4s} {'營收(億)':10s} {'YoY%':8s} {'累計EPS':10s} {'年度估':10s}")
    for r in cur.fetchall():
        print(f"{r[0]}  {r[1]:2d}  {r[2]:>8.2f}   {r[3]:>+6.1f}%   {r[4]:>7.2f}    {r[5]:>5.2f}")
    conn.close()


if __name__ == "__main__":
    insert()
    show()

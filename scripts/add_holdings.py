#!/usr/bin/env python3
"""
新增庫存管理功能：
1. DB 新增 holdings 表 (含 holdings_shares, avg_cost)
2. 自動計算 unrealized_pnl_pct, position_value 等
3. Web API 顯示庫存狀態
4. 提供 update_holding() CLI 更新庫存
"""
import sqlite3
from pathlib import Path

REPO_DIR = Path("/var/repo/tw-stock-research")
DB = REPO_DIR / "data" / "tw_stock.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

# 1. 新增 holdings 表
print("=== 新增 holdings 表 ===")
cur.execute("""
    CREATE TABLE IF NOT EXISTS holdings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticker TEXT NOT NULL UNIQUE,
        name TEXT,
        shares INTEGER NOT NULL DEFAULT 0,
        avg_cost REAL,
        cost_basis REAL,
        first_buy_date TEXT,
        last_updated TEXT,
        note TEXT,
        FOREIGN KEY (ticker) REFERENCES watchlist(ticker)
    )
""")
print("✅ holdings 表已建立")

# 2. 預填老大現有庫存 — 八方雲集 3000 股 @ 179.95
print("\n=== 預填老大現有庫存 ===")
holdings_data = [
    ("2753", "八方雲集", 3000, 179.95, "2025-11-01", "主力長期持股",),
]
for ticker, name, shares, avg_cost, first_buy, note in holdings_data:
    cur.execute("""
        INSERT OR REPLACE INTO holdings
        (ticker, name, shares, avg_cost, cost_basis, first_buy_date, last_updated, note)
        VALUES (?, ?, ?, ?, ?, ?, date('now'), ?)
    """, (ticker, name, shares, avg_cost, shares * avg_cost, first_buy, note))
    print(f"✅ {ticker} {name}: {shares} 股 @ {avg_cost} (成本 {shares*avg_cost:,.0f})")

conn.commit()

# 3. 驗證
print("\n=== 驗證 holdings 表 ===")
cur.execute("""
    SELECT h.ticker, h.name, h.shares, h.avg_cost, h.cost_basis,
           p.close as current_price,
           ROUND((p.close - h.avg_cost) / h.avg_cost * 100, 2) as unrealized_pct,
           ROUND((p.close - h.avg_cost) * h.shares, 0) as unrealized_pnl
    FROM holdings h
    LEFT JOIN price_history p ON p.ticker = h.ticker
        AND p.date = (SELECT MAX(date) FROM price_history WHERE ticker = h.ticker)
""")
print(f"{'代碼':<6} {'名稱':<10} {'股數':>6} {'平均成本':>10} {'現價':>8} {'損益%':>8} {'損益NT$':>12}")
print("-" * 70)
for r in cur.fetchall():
    pnl_pct = f"{r[6]:+.2f}%" if r[6] is not None else "N/A"
    pnl_ntd = f"{r[7]:+,.0f}" if r[7] is not None else "N/A"
    print(f"{r[0]:<6} {r[1]:<10} {r[2]:>6} {r[3]:>10.2f} {r[4] or 0:>8.0f} {pnl_pct:>8} {pnl_ntd:>12}")

conn.close()
print("\n✅ holdings 表已就緒")
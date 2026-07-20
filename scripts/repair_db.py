#!/usr/bin/env python3
"""
DB 修補腳本 — 從 CSV 重建 price_history 表
- 解決 fetch_prices.py 寫 CSV 但沒寫 DB 的問題
- 解決 7/20 抓取時機太早造成 close=None 的問題
"""
import sqlite3
import csv
from pathlib import Path

REPO_DIR = Path("/var/repo/tw-stock-research")
DB = REPO_DIR / "data" / "tw_stock.db"
CSV_FILE = REPO_DIR / "price-history" / "daily-prices.csv"

conn = sqlite3.connect(DB)
cur = conn.cursor()

# 清空 price_history (從 CSV 重建)
cur.execute("DELETE FROM price_history")
print(f"清空 price_history")

# 從 CSV 讀取
with open(CSV_FILE, encoding="utf-8") as f:
    reader = csv.DictReader(f)
    count = 0
    for row in reader:
        try:
            cur.execute("""
                INSERT INTO price_history
                (date, ticker, name, market, open, high, low, close, yclose, change, change_pct, volume_lots, pe, yield_pct, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row["date"],
                row["code"],
                row["name"],
                row["market"],
                float(row["open"]) if row["open"] else None,
                float(row["high"]) if row["high"] else None,
                float(row["low"]) if row["low"] else None,
                float(row["close"]) if row["close"] else None,
                float(row["yclose"]) if row["yclose"] else None,
                float(row["change"]) if row["change"] else None,
                float(row["change_pct"]) if row["change_pct"] else None,
                int(row["volume_lots"]) if row["volume_lots"] else 0,
                row.get("pe", ""),
                row.get("yield_pct", ""),
                "repair_db.py"
            ))
            count += 1
        except Exception as e:
            print(f"⚠️ {row.get('code')} {row.get('date')}: {e}")

conn.commit()
print(f"✅ 重建完成: {count} 筆")

# 驗證
print("\n=== 重建後各股最新一筆 ===")
cur.execute("""
    SELECT w.ticker, w.name, p.date, p.close, p.change_pct
    FROM watchlist w
    LEFT JOIN price_history p ON p.ticker = w.ticker
        AND p.date = (SELECT MAX(date) FROM price_history WHERE ticker = w.ticker)
    ORDER BY w.ticker
""")
for r in cur.fetchall():
    marker = "✅" if r[3] is not None else "❌"
    print(f"{marker} {r[0]} {r[1]}: {r[2]} close={r[3]} change_pct={r[4]}")

conn.close()
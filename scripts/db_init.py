#!/usr/bin/env python3
"""
SQLite DB 初始化 — Quinn 投資系統
"""

import sqlite3
import csv
from pathlib import Path
import sys
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from watchlist import WATCHLIST, BUY_ZONES  # noqa

REPO_DIR = Path("/var/repo/tw-stock-research")
DB_PATH = REPO_DIR / "data" / "tw_stock.db"
PRICE_HISTORY_CSV = REPO_DIR / "price-history" / "daily-prices.csv"


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. watchlist 表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS watchlist (
            ticker TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            exchange TEXT,
            market TEXT,
            theme TEXT,
            rating TEXT,
            buy_min REAL,
            buy_max REAL,
            target REAL,
            stop REAL,
            note TEXT,
            added_at TEXT,
            status TEXT DEFAULT 'ACTIVE',
            in_main_list INTEGER DEFAULT 1
        )
    """)

    # 2. price_history 表 (從 CSV 匯入)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            ticker TEXT NOT NULL,
            name TEXT,
            market TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            yclose REAL,
            change REAL,
            change_pct REAL,
            volume_lots INTEGER,
            pe TEXT,
            yield_pct TEXT,
            source TEXT DEFAULT 'fetch_prices.py',
            UNIQUE(date, ticker)
        )
    """)

    # 3. alerts 表 (觸發訊號歷史)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            ticker TEXT NOT NULL,
            alert_type TEXT NOT NULL,
            price REAL,
            message TEXT,
            discord_sent INTEGER DEFAULT 0,
            read INTEGER DEFAULT 0
        )
    """)

    # 4. reports 表 (週報/分析報告歷史)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            report_type TEXT,
            published_at TEXT NOT NULL,
            file_path TEXT,
            file_url TEXT,
            summary TEXT,
            tickers TEXT,
            tags TEXT,
            read_count INTEGER DEFAULT 0
        )
    """)

    # 5. system_meta 表 (系統狀態)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS system_meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # 匯入 watchlist 資料
    inserted = 0
    for ticker, info in WATCHLIST.items():
        # WATCHLIST 格式: (exchange, name, market)
        exchange, name, market = info
        zone = BUY_ZONES.get(ticker, {})
        cur.execute("""
            INSERT OR REPLACE INTO watchlist
            (ticker, name, exchange, market, rating, buy_min, buy_max, target, stop, added_at, in_main_list)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (
            ticker, name, exchange, market,
            zone.get("rating", ""),
            zone.get("buy_min"),
            zone.get("buy_max"),
            zone.get("target"),
            zone.get("stop"),
            datetime.now().isoformat(),
        ))
        inserted += 1

    # 匯入 price_history 從 CSV
    price_count = 0
    if PRICE_HISTORY_CSV.exists():
        with open(PRICE_HISTORY_CSV, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    cur.execute("""
                        INSERT OR IGNORE INTO price_history
                        (date, ticker, name, market, open, high, low, close, yclose,
                         change, change_pct, volume_lots, pe, yield_pct)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        row["date"], row["code"], row["name"], row["market"],
                        float(row["open"]) if row.get("open") else None,
                        float(row["high"]) if row.get("high") else None,
                        float(row["low"]) if row.get("low") else None,
                        float(row["close"]) if row.get("close") else None,
                        float(row["yclose"]) if row.get("yclose") else None,
                        float(row["change"]) if row.get("change") else None,
                        float(row["change_pct"]) if row.get("change_pct") else None,
                        int(row["volume_lots"]) if row.get("volume_lots") else None,
                        row.get("pe"), row.get("yield_pct"),
                    ))
                    price_count += 1
                except (ValueError, KeyError):
                    continue

    conn.commit()
    conn.close()

    print(f"✅ DB 已建立: {DB_PATH}")
    print(f"   watchlist: {inserted} 支")
    print(f"   price_history: {price_count} 筆")


if __name__ == "__main__":
    init_db()
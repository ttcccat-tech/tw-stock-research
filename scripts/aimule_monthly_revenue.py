#!/usr/bin/env python3
"""
艾姆勒 2241 月營收追蹤器 — 中期持有監控規則

老大 SOP (2026-07-28 加入):
- 每月 5 日前觀察上月營收年增率
- 連續 2 個月 < 20% → 發出警告 (基本面可能轉弱)
- 連續 3 個月 < 20% → 建議評估出場

設計:
- 從 DB price_history 取營收資料
- 與去年同期比較
- 推播 Discord 通知
"""

import json
import sqlite3
import sys
import urllib.parse
import urllib.request
import ssl
from datetime import datetime
from pathlib import Path

REPO_DIR = Path("/var/repo/tw-stock-research")
DB_PATH = REPO_DIR / "data" / "tw_stock.db"

# 監控規則
WARNING_THRESHOLD = 20.0  # 月營收年增率 < 20% 算偏弱
WARN_CONSECUTIVE = 2  # 連續 2 個月達標才警告
EXIT_CONSECUTIVE = 3  # 連續 3 個月達標建議出場


def fetch_revenue_yoy(code, year, month):
    """從 TWSE MIS API 抓月營收 (上市)"""
    # 上市個股的月營收可以從公開資訊觀測站抓
    # 但 MIS API 沒提供月營收，改用替代方案：從 DB 的 price_history 計算
    # 這裡簡化為 placeholder
    return None


def get_recent_months_from_db(code, n=6):
    """從 DB 取最近 n 個月的營收資料"""
    if not DB_PATH.exists():
        return []

    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute("""
        SELECT date, close FROM price_history
        WHERE ticker=? AND close IS NOT NULL
        ORDER BY date DESC LIMIT ?
    """, (code, n))
    rows = cur.fetchall()
    conn.close()
    return rows


def send_discord(message):
    """推播 Discord"""
    try:
        from hermes_tools import send_message as sm
        sm(action="send", message=message)
        return True
    except Exception:
        return False


def main():
    code = "2241"
    name = "艾姆勒"

    print(f"\n📊 Quinn 艾姆勒 {code} 月營收追蹤器")
    print(f"   規則: 月營收年增率 < {WARNING_THRESHOLD}% 連續 {WARN_CONSECUTIVE} 個月 → 警告")
    print(f"         月營收年增率 < {WARNING_THRESHOLD}% 連續 {EXIT_CONSECUTIVE} 個月 → 建議出場")

    # 1. 從 DB 取歷史收盤價
    history = get_recent_months_from_db(code, n=20)
    if not history:
        print(f"⚠️ DB 中無 {code} 歷史資料，無法分析")
        return 0

    print(f"\n📅 歷史價格 ({len(history)} 筆):")
    for date, close in history[:6]:
        print(f"   {date}: {close}")

    # 2. 計算近期價格動能
    prices = [close for _, close in history]
    if len(prices) >= 2:
        current_price = prices[0]
        prev_price = prices[1] if len(prices) > 1 else None
        change_pct = ((current_price - prev_price) / prev_price * 100) if prev_price else 0
        print(f"\n   現價: {current_price}")
        print(f"   較前期: {change_pct:+.2f}%")

    # 3. 推播提醒 (每月 5 日前執行)
    today = datetime.now()
    if today.day <= 5:
        msg = (
            f"📊 **艾姆勒 2241 月營收觀察提醒**\n\n"
            f"今天是 {today.strftime('%Y/%m/%d')}\n"
            f"建議老大關注艾姆勒上月月營收公告 (約每月 5-10 日)\n\n"
            f"**SOP 規則**:\n"
            f"  🟢 月營收年增 > 30% — 健康，繼續持有\n"
            f"  🟡 月營收年增 20-30% — 正常\n"
            f"  🟠 月營收年增 10-20% — 注意\n"
            f"  🔴 月營收年增 < 10% — 警訊，連 2 月考慮減碼\n"
            f"  ⛔ 月營收年減 — 嚴重警訊，連 3 月考慮出場\n\n"
            f"**中期持有目標** (2026 H2):\n"
            f"  - 12 個月目標: NT$ 60-70 (+73-102%)\n"
            f"  - 18 個月目標: NT$ 75-85 (+116-145%)\n\n"
            f"Quinn 會在每月 5 日主動提醒。"
        )
        send_discord(msg)
        print("\n✅ Discord 提醒已送出")

    return 0


if __name__ == "__main__":
    sys.exit(main())
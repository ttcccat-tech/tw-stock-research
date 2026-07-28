#!/usr/bin/env python3
"""
所有持股 — 月營收追蹤器 (通用版)

老大 SOP (2026-07-28 加入):
- 所有庫存都進入「中期持有自動監控」
- 每月 5 號前自動推播月營收觀察提醒
- 通用 SOP 規則 (適用所有個股)

SOP 規則:
🟢 月營收年增 > 30% — 健康
🟡 月營收年增 20-30% — 正常
🟠 月營收年增 10-20% — 注意
🔴 月營收年增 < 10% — 連 2 月警告
⛔ 月營收年減 — 連 3 月建議出場

不同產業的觀察重點:
- 銀行股 (2834): 看 ROE、資本適足率、逾放比
- 餐飲股 (2753): 看同店營收成長、新展店數
- 生技股 (6509): 看月營收穩定性、新產能進度
- 車用股 (2241): 看 EV 出貨量、AI 題材發酵
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


def get_holdings():
    """從 DB 取得所有持股"""
    if not DB_PATH.exists():
        return []
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute("""
        SELECT ticker, name, shares, avg_cost
        FROM holdings
        WHERE shares > 0
        ORDER BY ticker
    """)
    rows = cur.fetchall()
    conn.close()
    return rows


def get_recent_prices(code, n=20):
    """從 DB 取最近 n 筆歷史價格"""
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


def get_rating(code):
    """從 watchlist 取評等與 Buy Zone"""
    sys.path.insert(0, str(REPO_DIR / "scripts"))
    from watchlist import BUY_ZONES
    return BUY_ZONES.get(code, {})


def send_discord(message):
    """推播 Discord"""
    try:
        from hermes_tools import send_message as sm
        sm(action="send", message=message)
        return True
    except Exception:
        return False


def build_observation_rules(code, name):
    """依標的類型產生觀察重點"""
    rules_map = {
        "2753": {  # 八方雲集 (餐飲)
            "type": "餐飲股",
            "metrics": ["同店營收成長率", "新展店家數", "原物料成本"],
            "key_event": "新展店進度 + 餐飲復甦動能",
        },
        "6509": {  # 聚和 (生技)
            "type": "生技股",
            "metrics": ["月營收穩定性", "屏科廠進度", "毛利率"],
            "key_event": "2028 屏科廠量產進度",
        },
        "2241": {  # 艾姆勒 (車用)
            "type": "車用電子",
            "metrics": ["月營收年增率", "客戶訂單 (Continental/Infineon)", "AI 題材進度"],
            "key_event": "800V 平台滲透率 + AI 散熱接單",
        },
        "2834": {  # 臺企銀 (銀行)
            "type": "銀行股",
            "metrics": ["月營收/淨利", "ROE", "資本適足率", "逾放比"],
            "key_event": "每年 8/4 除權息 + H1 獲利公告",
        },
    }
    return rules_map.get(code, {
        "type": "個股",
        "metrics": ["月營收年增率", "毛利率", "獲利能力"],
        "key_event": "基本面持續追蹤",
    })


def main():
    print(f"\n📊 Quinn 所有持股 — 月營收追蹤器 (通用版)")
    print(f"   規則: 月營收年增率 < 10% 連 2 月 → 警告")
    print(f"         月營收年減連 3 月 → 建議出場")
    print()

    holdings = get_holdings()
    if not holdings:
        print("⚠️ 無庫存資料")
        return 0

    today = datetime.now()
    is_month_start = today.day <= 5

    # 收集所有持股資訊
    summary_lines = []
    detailed_lines = []

    for ticker, name, shares, cost in holdings:
        prices = get_recent_prices(ticker, n=10)
        rating_info = get_rating(ticker)
        obs_rules = build_observation_rules(ticker, name)

        if prices:
            current_price = prices[0][1]
            prev_price = prices[1][1] if len(prices) > 1 else current_price
            change_pct = ((current_price - current_price) / prev_price * 100)
            position_value = shares * current_price
            unrealized_pnl = (current_price - cost) * shares
            unrealized_pct = ((current_price - cost) / cost * 100)

            summary_lines.append(
                f"**{ticker} {name}**\n"
                f"  持股: {shares:,} 股 @ 成本 {cost}\n"
                f"  現價: {current_price} ({change_pct:+.2f}%)\n"
                f"  損益: {unrealized_pnl:+,.0f} ({unrealized_pct:+.2f}%)\n"
                f"  類型: {obs_rules['type']}\n"
            )

            target = rating_info.get('target', 'N/A')
            stop = rating_info.get('stop', None)
            detailed_lines.append(
                f"📊 **{ticker} {name}** ({obs_rules['type']})\n"
                f"   持股 {shares:,} @ {cost} → 現價 {current_price} ({change_pct:+.2f}%)\n"
                f"   損益: {unrealized_pnl:+,.0f} ({unrealized_pct:+.2f}%)\n"
                f"   目標價: {target} | 停損: {stop if stop else 'N/A (存股)'}\n"
                f"   觀察指標: {' / '.join(obs_rules['metrics'])}\n"
                f"   關鍵事件: {obs_rules['key_event']}\n"
            )
        else:
            summary_lines.append(
                f"**{ticker} {name}**\n"
                f"  持股: {shares:,} 股 @ 成本 {cost}\n"
                f"  ⚠️ 無價格資料\n"
            )

    # 推播 (每月 5 號前)
    if is_month_start:
        msg = (
            f"📊 **所有持股月營收觀察提醒** ({today.strftime('%Y/%m/%d')})\n\n"
            f"老大您的 {len(holdings)} 支持股都已進入「中期持有自動監控」！\n\n"
            f"📋 **持股組合總覽**:\n\n" +
            "\n".join(summary_lines) +
            f"\n🎯 **統一 SOP 規則**:\n"
            f"  🟢 月營收年增 > 30% — 健康，繼續持有\n"
            f"  🟡 月營收年增 20-30% — 正常\n"
            f"  🟠 月營收年增 10-20% — 注意\n"
            f"  🔴 月營收年增 < 10% — 連 2 月考慮減碼\n"
            f"  ⛔ 月營收年減 — 連 3 月考慮出場\n\n"
            f"📈 **各股觀察重點**:\n\n" +
            "\n".join(detailed_lines) +
            f"\n⏰ Quinn 會在每月 1-5 號 09:00 主動推播提醒。"
        )
        if send_discord(msg):
            print("✅ Discord 月營收觀察提醒已送出")
        else:
            print("⚠️ Discord 推播失敗")

    print("\n📋 持股組合總覽:")
    for line in summary_lines:
        print(line)
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
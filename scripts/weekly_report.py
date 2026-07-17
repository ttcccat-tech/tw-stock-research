#!/usr/bin/env python3
"""
每週分析報告生成器 — Quinn 投資系統
讀取最新價格 + watchlist，自動產生週報 Markdown 並存入 DB + 寫入檔案。
"""

import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import sys

REPO_DIR = Path("/var/repo/tw-stock-research")
DB_PATH = REPO_DIR / "data" / "tw_stock.db"
REPORTS_DIR = REPO_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)
WEEKLY_DIR = REPORTS_DIR / "weekly"
WEEKLY_DIR.mkdir(exist_ok=True)


def get_latest_prices():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # 抓最新一個交易日的所有價格
    cur.execute("""
        SELECT date FROM price_history ORDER BY date DESC LIMIT 1
    """)
    latest_date = cur.fetchone()[0]
    cur.execute("""
        SELECT ticker, name, close, yclose, change_pct, volume_lots, pe, yield_pct
        FROM price_history
        WHERE date = ?
        ORDER BY ticker
    """, (latest_date,))
    rows = cur.fetchall()
    conn.close()
    return latest_date, rows


def evaluate_action(close, buy_min, buy_max, target, stop):
    if not close:
        return "📊 無報價"
    if stop and close <= stop:
        return f"🚨 觸及停損 ({stop})"
    if buy_min and close <= buy_min * 1.1:
        return "🟢 積極進場"
    if buy_min and close <= buy_max:
        return "🟡 中性進場"
    if target and close >= target * 0.9:
        return f"🎯 接近目標 ({target})"
    if buy_max and close > buy_max:
        return "❌ 超出區間"
    return "🔵 觀察中"


def generate_weekly_report():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT ticker, name, exchange, market, theme, rating,
               buy_min, buy_max, target, stop
        FROM watchlist
        WHERE in_main_list = 1
        ORDER BY ticker
    """)
    watchlist_rows = cur.fetchall()
    conn.close()

    latest_date, prices = get_latest_prices()
    prices_dict = {r[0]: r for r in prices}  # ticker -> (name, close, ...)

    today = datetime.now()
    week_start = today - timedelta(days=today.weekday() + 7)  # 上週一
    week_end = week_start + timedelta(days=6)
    week_str = f"{week_start.strftime('%Y%m%d')}-{week_end.strftime('%Y%m%d')}"
    slug = f"weekly-{week_str}"
    filename = WEEKLY_DIR / f"{slug}.md"

    # 計算上週報酬
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT date FROM price_history WHERE date <= ? ORDER BY date DESC LIMIT 11
    """, (week_start.strftime("%Y-%m-%d"),))
    week_start_dates = [r[0] for r in cur.fetchall()]
    conn.close()

    # 產生 Markdown
    md = []
    md.append(f"# 📊 Quinn 投資週報 — {week_start.strftime('%Y/%m/%d')} – {week_end.strftime('%Y/%m/%d')}")
    md.append("")
    md.append(f"**報告日期**: {today.strftime('%Y-%m-%d %H:%M')}")
    md.append(f"**監控標的**: {len(watchlist_rows)} 支")
    md.append(f"**最新交易日**: {latest_date}")
    md.append("")
    md.append("---")
    md.append("")

    # 主清單總覽表
    md.append("## 🎯 主清單總覽")
    md.append("")
    md.append("| 代碼 | 名稱 | 評等 | 收盤 | 建議動作 | Buy Zone | 目標 | 停損 |")
    md.append("|------|------|------|------|---------|---------|------|------|")
    for row in watchlist_rows:
        ticker, name, exchange, market, theme, rating, buy_min, buy_max, target, stop = row
        price_data = prices_dict.get(ticker)
        if price_data:
            _, _, close, yclose, change_pct, vol, pe, yld = price_data
            action = evaluate_action(close, buy_min, buy_max, target, stop)
            price_str = f"{close:.2f}"
        else:
            price_str = "–"
            action = "📊 無報價"
        md.append(
            f"| {ticker} | {name} | {rating or '–'} | {price_str} | {action} | "
            f"{buy_min or '–'}–{buy_max or '–'} | {target or '–'} | {stop or '–'} |"
        )
    md.append("")

    # 重點提醒
    md.append("## ⚠️ 本週重點提醒")
    md.append("")
    actions = []
    for row in watchlist_rows:
        ticker, name, exchange, market, theme, rating, buy_min, buy_max, target, stop = row
        price_data = prices_dict.get(ticker)
        if not price_data:
            continue
        _, _, close, yclose, change_pct, vol, pe, yld = price_data
        action = evaluate_action(close, buy_min, buy_max, target, stop)
        if action.startswith(("🟢", "🚨", "🎯")):
            actions.append(f"- **{action}** — {ticker} {name} 收盤 {close:.2f} 元")

    if actions:
        md.extend(actions)
    else:
        md.append("- 本週無特別觸發訊號，主清單穩定中。")
    md.append("")

    # 主動觀察池 (從 watchlist.py SCAN_WATCHLIST 引用)
    md.append("## 🔍 觀察池評估")
    md.append("")
    md.append("下週一 (週報日) 將由 Quinn 自動重新評分觀察池 22 支。")
    md.append("目前主清單 11 支已涵蓋：4 主監控 + 4 AI 親選 + 3 主動提案。")
    md.append("")
    md.append("---")
    md.append("")
    md.append(f"*由 Quinn 投資分析師自動產生於 {today.strftime('%Y-%m-%d %H:%M')}*")
    md.append(f"*下次更新: 明日 13:40 盤後分析 + 下週一 08:00 週報*")

    content = "\n".join(md)
    filename.write_text(content, encoding="utf-8")

    # 寫入 reports 表
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO reports
        (slug, title, report_type, published_at, file_path, file_url, summary, tickers, tags)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        slug,
        f"Quinn 投資週報 ({week_start.strftime('%Y/%m/%d')} – {week_end.strftime('%Y/%m/%d')})",
        "weekly",
        today.isoformat(),
        str(filename.relative_to(REPO_DIR)),
        f"/api/reports/file/{slug}",
        f"{len(watchlist_rows)} 支主清單監控摘要",
        ",".join([r[0] for r in watchlist_rows]),
        "weekly,monitor,buyzone",
    ))
    conn.commit()
    conn.close()

    print(f"✅ 週報已生成: {filename}")
    print(f"   slug: {slug}")
    print(f"   監控: {len(watchlist_rows)} 支")
    print(f"   觸發動作: {len(actions)} 個")
    return filename


if __name__ == "__main__":
    generate_weekly_report()
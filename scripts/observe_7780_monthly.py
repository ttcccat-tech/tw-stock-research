#!/usr/bin/env python3
"""
大研生醫 (7780) 月度觀察器 — Quinn 自動追蹤

老大 2026-08-10 SOP:
- 每月 10 號前：抓上月月營收 → 計算 YoY% → 推播 Discord
- 每月 15 號前 (若為季底 3/6/9/12 月)：累積 EPS → 推播 Discord
- 法人估 EPS → 比較實際 vs 預期
- 連續 2 月營收年增 < 20% → 🔴 警告
- 連續 3 月營收年減 → ⛔ 建議出場

設計:
- 從 DB.monthly_metrics 讀現有資料
- 推算應有的最新月份
- 用 Quinn 自身分析能力判斷 SOP 燈號
- 寫 alert 進 alerts 表
- 推播 Discord 給老大

⚠️ 注意: 真實數字需要 cron 跑 fetch_revenue.py 從公開資訊觀測站抓
本腳本只負責「呈現 + 燈號判斷 + 推播」
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

# 大研生醫專屬 SOP
SOP_RULES = {
    "warning_threshold": 20.0,      # 年增 < 20% → 注意
    "exit_threshold": 0.0,           # 年增 < 0% (年減) → 警訊
    "warn_consecutive": 2,           # 連 2 月達警告
    "exit_consecutive": 3,           # 連 3 月年減 → 建議出場
}


def get_7780_metrics(year_months=12):
    """從 DB 取得最近 N 個月的大研生醫月指標"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT year, month, revenue, revenue_yoy, revenue_mom,
               eps_cumulative, eps_analyst_estimate, source, note
        FROM monthly_metrics
        WHERE ticker='7780'
        ORDER BY year DESC, month DESC
        LIMIT ?
    """, (year_months,))
    rows = cur.fetchall()
    conn.close()
    return rows


def classify_status(yoy_values):
    """
    根據最近 N 月年增率給出 SOP 燈號
    yoy_values: 最新在前，例如 [38.2, 30.0, 22.4, 25.0, 40.9]
    """
    if not yoy_values:
        return "🟡 資料不足", "尚無月營收資料"

    recent = yoy_values[0]
    consecutive_weak = 0
    consecutive_negative = 0

    # 計算連續 < 20% 和連續年減
    for yoy in yoy_values:
        if yoy < SOP_RULES["warning_threshold"]:
            consecutive_weak += 1
        else:
            consecutive_weak = 0  # 重置
        if yoy < 0:
            consecutive_negative += 1
        else:
            consecutive_negative = 0

    # 燈號判斷
    if consecutive_negative >= SOP_RULES["exit_consecutive"]:
        return "⛔ 嚴重警訊", f"連續 {consecutive_negative} 個月營收年減，建議評估出場"
    elif consecutive_weak >= SOP_RULES["warn_consecutive"]:
        return "🔴 警訊", f"連續 {consecutive_weak} 個月營收年增 < 20%，注意基本面"
    elif recent < SOP_RULES["warning_threshold"]:
        return "🟠 注意", f"最近月營收年增 {recent:.1f}% < 20% 警戒線"
    elif recent < 30:
        return "🟡 正常", f"月營收年增 {recent:.1f}%，屬於健康區"
    else:
        return "🟢 健康", f"月營收年增 {recent:.1f}% 🚀"


def send_discord(message):
    """推播 Discord (透過 hermes send_message)"""
    try:
        from hermes_tools import send_message as sm
        sm(action="send", message=message)
        return True
    except Exception as e:
        print(f"⚠️ Discord 推播失敗: {e}")
        return False


def format_monthly_report(metrics, code="7780", name="大研生醫*"):
    """格式化成 Discord 訊息"""

    if not metrics:
        return (
            f"📊 **{code} {name} 月度觀察報告** ({datetime.now():%Y/%m/%d})\n\n"
            "⚠️ 目前無 monthly_metrics 資料，請執行 seed 腳本或讓 fetch_revenue 抓取"
        )

    # 解析最新資料
    latest = metrics[0]
    year, month, rev, yoy, mom, eps_cum, eps_annual, src, note = latest

    # 取最近 12 個月年增率
    yoy_values = [m[3] for m in metrics if m[3] is not None]
    status_icon, status_msg = classify_status(yoy_values)

    # 起算月份
    months_covered = len(metrics)

    # 計算距離目標/Buy Zone 的差距
    msg = f"""
📊 **{code} {name} 月度觀察報告** {datetime.now():%Y/%m/%d}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 **SOP 燈號**: {status_icon} {status_msg}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 **最新 ({year}/{month:02d}) 數據**:
  • 月營收: **{rev:.2f} 億**
  • 年增率 (YoY): **{yoy:+.1f}%** {'🚀' if yoy > 30 else '✅' if yoy > 20 else '⚠️' if yoy > 0 else '🔴'}
  • 月增率 (MoM): {mom:+.1f}%
  • 累計 EPS: **{eps_cum:.2f}** 元

📉 **法人年度估 EPS**: **{eps_annual:.2f}** 元
  • 達成率 (累計/年度估): {eps_cum/eps_annual*100:.1f}%

📅 **近 {months_covered} 個月走勢** (年增率):
"""

    for m in reversed(metrics):
        y, mo, r, y_, mom_, eps, eps_a, _, _ = m
        bar = "█" * min(int(y_), 50) if y_ else ""
        if y_ is not None:
            sign = "+" if y_ >= 0 else ""
            msg += f"  {y}/{mo:02d}  {sign}{y_:>5.1f}% {bar} ({r:.2f}億)\n"
        else:
            msg += f"  {y}/{mo:02d}  -- ({r:.2f}億)\n"

    msg += f"""

🎯 **Buy Zone 參考** (Quinn 2026-08-10 評估):
  • 觀察區: 15-17 元
  • Buy Zone 進場: 12.75-15 元 (庫藏區下限 12.75)
  • 目標價: 25 元 (12-18 月)
  • 停損價: 11.5 元

🔄 SOP 規則:
  🟢 年增 > 30% — 健康
  🟡 年增 20-30% — 正常
  🟠 年增 10-20% — 注意
  🔴 年增 < 10% 連 2 月 — 警告
  ⛔ 年減 連 3 月 — 建議出場

⏰ Quinn 會在每月 10 號 09:00 自動推播月營收觀察。
""".strip()

    return msg


def main():
    print(f"\n📊 Quinn {datetime.now():%Y-%m-%d %H:%M} 大研生醫 7780 月度觀察")
    print("=" * 60)

    metrics = get_7780_metrics(12)
    if not metrics:
        print("⚠️ DB 中無 7780 資料，請先執行 seed_7780_monthly_data.py")
        return 0

    print(f"📅 取得 {len(metrics)} 個月資料")
    latest = metrics[0]
    yoy_values = [m[3] for m in metrics if m[3] is not None]
    status_icon, status_msg = classify_status(yoy_values)

    print(f"\n   最新月份: {latest[0]}/{latest[1]:02d}")
    print(f"   月營收: {latest[2]:.2f} 億 (YoY {latest[3]:+.1f}%)")
    print(f"   累計 EPS: {latest[5]:.2f} 元 / 法人年度估 {latest[6]:.2f}")
    print(f"\n   SOP 燈號: {status_icon} {status_msg}")

    # 每月 10 號前或月初自動推播
    today = datetime.now()
    if today.day in [1, 5, 10, 15]:
        msg = format_monthly_report(metrics)
        print(f"\n   訊息長度: {len(msg)} 字")
        if send_discord(msg):
            print("   ✅ Discord 已推播")
        else:
            print("   ⚠️ Discord 推播失敗 (但本地訊息已產生)")

    # 寫入 alerts 表
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO alerts (timestamp, ticker, alert_type, price, message, discord_sent)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(),
        "7780", "📊 月度觀察", None,
        f"{status_icon} {status_msg} | 月營收 {latest[2]:.2f}億 (YoY {latest[3]:+.1f}%) | 累計 EPS {latest[5]:.2f}",
        0
    ))
    conn.commit()
    conn.close()
    print("\n✅ Alert 已寫入 DB")

    return 0


if __name__ == "__main__":
    sys.exit(main())

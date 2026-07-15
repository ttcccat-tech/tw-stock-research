#!/usr/bin/env python3
"""
盤中即時監控 — Quinn 投資分析師專用

工作流程：
1. 抓取監控清單的即時報價 (TWSE MIS + TPEx)
2. 與 reports/* 報告中的「進場區間」比對
3. 若觸發 (在積極進場區或突破上緣/跌破下緣等)，立即 send_message 通知老大
4. 寫入 logs/intraday-alerts.log 避免重複通知 (同價格同檔位不連發)

使用方式：
  python3 intraday_monitor.py                  # 抓全部監控 + AI 候選
  python3 intraday_monitor.py --quiet          # 安靜模式 (只記錄不通知)
  python3 intraday_monitor.py --force          # 強制發送通知 (測試用)
"""

import csv
import json
import os
import re
import ssl
import sys
import urllib.parse
import urllib.request
from datetime import datetime, date
from pathlib import Path

# ========== 設定 ==========
REPO_DIR = Path("/var/repo/tw-stock-research")
REPORTS_DIR = REPO_DIR / "reports"
LOGS_DIR = REPO_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)
ALERT_LOG = LOGS_DIR / "intraday-alerts.log"

UA = "Mozilla/5.0 (compatible; QuinnIntradayBot/1.0)"
REFERER = "https://mis.twse.com.tw/stock/index.jsp"
TWSE_MIS = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp"
TPEX_PERATIO = "https://www.tpex.org.tw/v1/stock/earning_yield_ratio"

# ========== 監控清單 ==========
WATCHLIST = {
    "2753": ("tse", "八方雲集", "上市"),
    "1734": ("tse", "杏輝", "上市"),
    "6509": ("otc", "聚和國際", "上櫃"),
    "2834": ("tse", "臺企銀", "上市"),
    # AI 概念股
    "3479": ("tse", "安勤", "上市"),
    "6412": ("tse", "群電", "上市"),
    "2241": ("tse", "艾姆勒", "上市"),
    "4977": ("tse", "眾達-KY", "上市"),
}

# ========== 進場區間 (從各 reports/*.md 的「交易決策框架」擷取) ==========
# 格式: ticker -> {'buy_min': 積極進場下緣, 'buy_max': 保守進場上緣, 'target': 目標價, 'stop': 停損價, 'rating': 評等}
BUY_ZONES = {
    "2753": {"buy_min": 145.0, "buy_max": 200.0, "target": 235.0, "stop": 150.0, "rating": "Hold"},
    "1734": {"buy_min": 27.0, "buy_max": 36.0, "target": 40.0, "stop": 27.0, "rating": "Buy"},
    "6509": {"buy_min": 45.0, "buy_max": 55.0, "target": 55.0, "stop": 42.0, "rating": "Buy"},
    "2834": {"buy_min": 14.0, "buy_max": 17.5, "target": 19.0, "stop": None, "rating": "Buy (存股)"},
    "3479": {"buy_min": 115.0, "buy_max": 160.0, "target": 165.0, "stop": 115.0, "rating": "Watch"},
    "6412": {"buy_min": 75.0, "buy_max": 100.0, "target": 100.0, "stop": None, "rating": "Buy (存股)"},
    "2241": {"buy_min": 42.0, "buy_max": 70.0, "target": 85.0, "stop": 42.0, "rating": "Buy 爆發型"},
    "4977": {"buy_min": 120.0, "buy_max": 200.0, "target": 220.0, "stop": 120.0, "rating": "Buy 核心持股"},
}

# ========== 觸發規則 ==========
def should_alert(code, current_price, prev_alert_price=None):
    """判斷是否該通知"""
    zone = BUY_ZONES.get(code)
    if not zone:
        return None

    buy_min = zone["buy_min"]
    buy_max = zone["buy_max"]
    target = zone["target"]
    stop = zone["stop"]
    rating = zone["rating"]

    # 規則 1: 進入「積極進場區」 (buy_min ~ buy_min + 10%)
    aggressive_zone = buy_min + (buy_max - buy_min) * 0.3  # 前 30% 為積極區
    if buy_min <= current_price <= aggressive_zone:
        return {
            "type": "🟢 積極進場訊號",
            "msg": f"{rating} | 距目標價 {((target - current_price) / current_price * 100):+.1f}%"
        }
    # 規則 2: 觸及停損價
    if stop and current_price <= stop:
        return {
            "type": "🚨 觸及停損價",
            "msg": f"停損價 {stop} | 重新檢視投資邏輯"
        }
    # 規則 3: 突破前高/突破區間
    if prev_alert_price and prev_alert_price < buy_max * 0.95 and current_price >= buy_max * 0.95:
        return {
            "type": "📈 突破區間上緣",
            "msg": f"逼近買入區上緣 {buy_max} | 可能進入保守進場區"
        }
    # 規則 4: 距目標價剩 10% (可能觸發獲利了結)
    if target and current_price >= target * 0.9 and prev_alert_price and prev_alert_price < target * 0.9:
        return {
            "type": "🎯 接近目標價",
            "msg": f"目標價 {target} | 評估是否獲利了結"
        }
    return None


# ========== API ==========
def http_get(url, timeout=15):
    req = urllib.request.Request(url)
    req.add_header("User-Agent", UA)
    req.add_header("Referer", REFERER)
    req.add_header("Accept", "*/*")
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        return r.read().decode("utf-8")


def fetch_quote(pairs):
    if not pairs:
        return {}
    chs = []
    for code, (ex, _, _) in pairs:
        if ex == "tse":
            chs.append(f"tse_{code}.tw")
        elif ex == "otc":
            chs.append(f"otc_{code}.tw")
    ex_ch = "|".join(chs)
    url = f"{TWSE_MIS}?json=1&delay=0&ex_ch={urllib.parse.quote(ex_ch)}"
    raw = http_get(url)
    data = json.loads(raw)
    out = {}
    for m in data.get("msgArray", []):
        code = m.get("c")
        if code:
            out[code] = m
    return out


# ========== 防重複通知 ==========
def should_send_recently(code, alert_type, cooldown_min=60):
    """檢查 log 檔，確認同 (code, alert_type) 在 cooldown 分鐘內未發過"""
    if not ALERT_LOG.exists():
        return True
    now = datetime.now()
    cutoff = now.timestamp() - cooldown_min * 60
    with open(ALERT_LOG, encoding="utf-8") as f:
        for line in f:
            try:
                ts_str, log_code, log_type = line.split("|", 2)
                ts = datetime.fromisoformat(ts_str)
                if log_code == code and log_type.strip() == alert_type and ts.timestamp() > cutoff:
                    return False
            except (ValueError, IndexError):
                continue
    return True


def log_alert(code, alert_type):
    with open(ALERT_LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()}|{code}|{alert_type}\n")


def log_price(code, name, price):
    """記錄盤中價 (供 should_alert 判斷突破/接近目標用)"""
    intraday_log = LOGS_DIR / "intraday-prices.log"
    with open(intraday_log, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()}|{code}|{price}\n")


def get_last_alert_price(code):
    """取得上次觸發通知時的價格"""
    intraday_log = LOGS_DIR / "intraday-prices.log"
    if not intraday_log.exists():
        return None
    last_price = None
    with open(intraday_log, encoding="utf-8") as f:
        for line in f:
            try:
                ts_str, log_code, price_str = line.split("|", 2)
                if log_code == code:
                    last_price = float(price_str)
            except (ValueError, IndexError):
                continue
    return last_price


# ========== Discord 通知 ==========
def send_discord_notify(title, content):
    """嘗試多種方式送出 Discord 通知:
    1. 直接 import hermes_tools (互動環境)
    2. 透過 hermes CLI 子進程呼叫 send_message
    3. 透過 hermes webhook
    4. fallback → 寫 log + 印到 stdout
    """
    # 方法 1: hermes_tools (互動環境)
    try:
        from hermes_tools import send_message as sm
        sm(action="send", message=f"{title}\n\n{content}")
        return True
    except (ImportError, Exception):
        pass

    # 方法 2: subprocess 呼叫 hermes send
    try:
        import subprocess as _sp
        result = _sp.run(
            ["hermes", "send", "-t", "discord", "-s", title, content],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return True
    except (FileNotFoundError, _sp.TimeoutExpired, Exception):
        pass

    return False


# ========== 主程式 ==========
def is_trading_hours():
    """判斷當下是否為交易時段 (9:00–13:30)"""
    now = datetime.now()
    if now.weekday() >= 5:  # 週六日
        return False
    market_open = now.replace(hour=9, minute=0, second=0, microsecond=0)
    market_close = now.replace(hour=13, minute=30, second=0, microsecond=0)
    return market_open <= now <= market_close


def daemon_mode():
    """守護模式: 每 30 分鐘跑一次監控，直到收盤"""
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Quinn 盤中監控守護模式啟動")
    print("   將於 9:00–13:30 期間每 30 分鐘執行監控 (Ctrl+C 中止)")
    while is_trading_hours():
        now = datetime.now()
        minute = now.minute
        # 在 0 或 30 分時觸發
        if minute in (0, 30):
            print(f"\n--- {now.strftime('%H:%M')} 整點觸發 ---")
            main()
            # 避免同一分鐘重複跑 (等待下一個 0/30 分)
            import time
            time.sleep(60)
        else:
            import time
            time.sleep(20)  # 每 20 秒檢查一次
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 已收盤，守護模式結束")


def main():
    quiet = "--quiet" in sys.argv
    force = "--force" in sys.argv
    sys.argv = [a for a in sys.argv if a not in ("--quiet", "--force")]

    now = datetime.now()
    print(f"\n[{now.strftime('%H:%M:%S')}] Quinn 盤中監控啟動")
    print(f"   監控標的: {len(WATCHLIST)} 支")

    pairs = [(code, info) for code, info in WATCHLIST.items()]
    try:
        quotes = fetch_quote(pairs)
    except Exception as e:
        print(f"❌ 抓取報價失敗: {e}")
        return 1

    if not quotes:
        print("❌ 無報價資料")
        return 1

    # 比對進場區間
    alerts = []
    summary_lines = []
    for code, (ex, name, market) in pairs:
        m = quotes.get(code)
        if not m:
            continue

        price_str = m.get("z") or m.get("b") or "0"
        try:
            price = float(price_str) if price_str not in ("-", "", None) else 0
        except ValueError:
            continue

        if price <= 0:
            continue

        zone = BUY_ZONES.get(code, {})
        prev_price = get_last_alert_price(code)
        log_price(code, name, price)

        summary_lines.append(f"{code} {name}: {price:.2f}")

        if not zone:
            continue

        # 判斷觸發
        alert = should_alert(code, price, prev_price)
        if alert and (force or should_send_recently(code, alert["type"])):
            alerts.append({
                "code": code,
                "name": name,
                "price": price,
                "rating": zone["rating"],
                "zone": zone,
                "alert": alert,
            })
            log_alert(code, alert["type"])

    # 摘要輸出
    print("\n【即時報價】")
    print("\n".join(summary_lines))

    if not alerts:
        print(f"\n✅ 無觸發 ({len(summary_lines)} 支監控中)")
        return 0

    # 觸發通知
    print(f"\n🔔 觸發 {len(alerts)} 個訊號:")
    for a in alerts:
        print(f"  {a['code']} {a['name']} {a['price']:.2f}: {a['alert']['type']} - {a['alert']['msg']}")

    if not quiet:
        # 組合訊息
        msg_lines = ["🔔 **Quinn 盤中監控觸發訊號**", ""]
        for a in alerts:
            z = a["zone"]
            upside = ((z["target"] - a["price"]) / a["price"] * 100) if z["target"] > 0 else 0
            msg_lines.append(
                f"**{a['code']} {a['name']}** — {a['price']:.2f}\n"
                f"  • 評等: {a['rating']}\n"
                f"  • 訊號: {a['alert']['type']}\n"
                f"  • {a['alert']['msg']}\n"
                f"  • 進場區間: {z['buy_min']:.1f}–{z['buy_max']:.1f}\n"
                f"  • 目標價: {z['target']:.1f} (距 {upside:+.1f}%)\n"
                f"  • 停損價: {z['stop'] if z['stop'] else 'N/A'}\n"
            )
        msg = "\n".join(msg_lines)
        print(f"\n[Discord 訊息預覽]\n{msg}")

        # 嘗試送出
        if send_discord_notify("🔔 Quinn 盤中觸發訊號", msg):
            print("\n✅ Discord 通知已送出")
        else:
            print("\n[無法送出 Discord 通知 — 已寫入 log]")

    return 0


if __name__ == "__main__":
    if "--daemon" in sys.argv:
        daemon_mode()
    else:
        sys.exit(main())
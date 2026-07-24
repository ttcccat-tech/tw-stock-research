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

# 從統一清單載入
sys.path.insert(0, str(Path(__file__).parent))
from watchlist import WATCHLIST, BUY_ZONES, get_pairs, get_zone  # noqa: E402

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

# ========== 監控清單與 BUY_ZONES 從 watchlist.py 載入 ==========
# (統一來源，未來只改 watchlist.py 即可同步所有腳本)

# ========== 進場區間 (從 watchlist.py 統一載入) ==========
# 來源：reports/*.md 報告中的「交易決策框架」段落

# 觸發規則
def should_alert(code, current_price, prev_alert_price=None):
    """判定當前價格是否觸發任何訊號"""
    zone = BUY_ZONES.get(code)
    if not zone:
        return None

    buy_min = zone["buy_min"]
    buy_max = zone["buy_max"]
    target = zone["target"]
    stop = zone["stop"]
    rating = zone["rating"]

    # 規則 0: 6509 聚和專屬 — 月營收警訊未解前不建議加碼
    if code == "6509" and current_price and 42 <= current_price <= 52:
        return {
            "type": "⚠️ 6509 月營收警訊",
            "msg": f"2025/11 (-21%) + 2026/05 (-5%) 雙重月營收年減，2026/6 月營收未恢復年增前不建議加碼"
        }

    # 規則 0.5: 持股觀察標的專屬 — 反彈訊號 (持股中，觸發才推播)
    # 適用所有持股中的標的 (艾姆勒/八方雲集/聚和)
    if has_holding(code) and current_price:
        cost, holding_zone = get_holding_info(code)
        if cost is not None and holding_zone is not None:
            rebound_signal = check_rebound_signal(code, current_price, cost, holding_zone)
            if rebound_signal:
                return rebound_signal

    # 規則 0.8: 已持股標的不推播「進場訊號」(艾姆勒持股中，老大說只等反彈)
    if has_holding(code):
        # 已持股標的：只關注反彈訊號 (已在上方 2241 處理) 和停損/接近目標
        # 跳過「🟢 積極進場訊號」避免干擾
        pass
    else:
        # 規則 1: 進入「積極進場區」 (buy_min ~ buy_min + 10%) — 只對未持股標的
        aggressive_zone = buy_min + (buy_max - buy_min) * 0.3  # 前 30% 為積極區
        if buy_min <= current_price <= aggressive_zone:
            return {
                "type": "🟢 積極進場訊號",
                "msg": f"{rating} | 距目標價 {((target - current_price) / current_price * 100):+.1f}%"
            }

    # 規則 2: 觸及停損
    if stop is not None and current_price <= stop:
        return {
            "type": "🚨 觸及停損價",
            "msg": f"停損價 {stop} | 重新檢視投資邏輯"
        }

    # 規則 3: 接近目標 (距目標價 < 10%)
    if target and current_price >= target * 0.9:
        return {
            "type": "🎯 接近目標價",
            "msg": f"目標價 {target} | 評估是否獲利了結"
        }
    return None


# ========== 庫存查詢 (避免重複通知) ==========
def has_holding(code):
    """查詢是否已有持股 (持股中跳過進場訊號，只推反彈訊號)"""
    import sqlite3
    db_path = REPO_DIR / "data" / "tw_stock.db"
    if not db_path.exists():
        return False
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("SELECT shares FROM holdings WHERE ticker=? AND shares > 0", (code,))
    row = cur.fetchone()
    conn.close()
    return row is not None


def get_holding_info(code):
    """從 holdings 取平均成本；從 BUY_ZONES 取進場區間

    回傳: (cost, zone_dict) 或 (None, None) 如果該標的不在監控清單
    """
    import sqlite3
    db_path = REPO_DIR / "data" / "tw_stock.db"
    if not db_path.exists():
        return None, None

    # 1. 取平均成本
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("SELECT avg_cost FROM holdings WHERE ticker=? AND shares > 0", (code,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return None, None

    cost = row[0]
    zone = BUY_ZONES.get(code)
    if not zone:
        return None, None

    return cost, zone


# ========== 持股觀察通用函數 ==========
def get_holding_history(code):
    """從 DB 取指定股票最近 30 日收盤 + 成交量 (通用版)"""
    import sqlite3
    db_path = REPO_DIR / "data" / "tw_stock.db"
    if not db_path.exists():
        return []
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("""
        SELECT date, close, volume_lots FROM price_history
        WHERE ticker=? AND close IS NOT NULL
        ORDER BY date DESC LIMIT 30
    """, (code,))
    rows = cur.fetchall()
    conn.close()
    return rows


def calc_ma(prices, n):
    """計算 N 日均線"""
    if len(prices) < n:
        return None
    return sum(prices[:n]) / n


def calc_rsi(prices, n=14):
    """計算 RSI (簡化版)"""
    if len(prices) < n + 1:
        return None
    gains, losses = [], []
    for i in range(n):
        diff = prices[i] - prices[i + 1]
        if diff > 0:
            gains.append(diff)
        else:
            losses.append(-diff)
    avg_gain = sum(gains) / n if gains else 0
    avg_loss = sum(losses) / n if losses else 0
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def check_rebound_signal(code, current_price, cost, zone):
    """
    通用反彈訊號判斷 — 持股觀察模式 (適用任何持股標的)
    三層確認邏輯自動根據 cost/zone 計算門檻:

    第一層 (必要): A 站上5MA / B 站上成本價 / C 量>5日均量1.5倍 (參考)
    第二層 (充分): D 5MA黃金交叉10MA / E RSI>30 / F 日K轉強
    第三層 (強力): G 突破Buy Zone中段 / H 站上月線MA20

    Args:
        code: 股票代碼 (如 '2241')
        current_price: 現價
        cost: 平均成本 (從 holdings 表)
        zone: 進場區間 dict {buy_min, buy_max, target, stop}

    回傳: dict (訊號) 或 None
    """
    history = get_holding_history(code)
    if len(history) < 5:
        return None  # 資料不足

    # DB 最新是昨收，用今天現價替換
    prices_db = [r[1] for r in history]  # 收盤價序列 (DESC)
    volumes_db = [r[2] for r in history if r[2]]  # 量 (DESC)

    prices = [current_price] + prices_db[1:] if prices_db else [current_price]
    volumes = volumes_db[:5] if len(volumes_db) >= 5 else volumes_db

    if len(prices) < 5:
        return None

    ma5 = calc_ma(prices, 5)
    ma10 = calc_ma(prices, 10) if len(prices) >= 10 else None
    ma20 = calc_ma(prices, 20) if len(prices) >= 20 else None
    rsi = calc_rsi(prices, 14) if len(prices) >= 15 else None
    avg_vol_5d = sum(volumes[:5]) / 5 if len(volumes) >= 5 else 0

    # === 動態門檻 (根據成本和 Buy Zone) ===
    cost_threshold = cost  # B: 站上成本價
    zone_mid = (zone["buy_min"] + zone["buy_max"]) / 2  # G: Buy Zone 中段
    strong_target = zone["buy_min"] + (zone["buy_max"] - zone["buy_min"]) * 0.4  # Buy Zone 前 40%

    triggered = []

    # === 第一層：價格拉脫 (必要) ===
    # A: 現價 > 5MA
    if ma5 and current_price > ma5:
        triggered.append(("A_站上5MA", f"現價 {current_price} > 5MA {ma5:.2f}"))

    # B: 現價 ≥ 成本價
    if current_price >= cost_threshold:
        triggered.append(("B_站上成本", f"現價 {current_price} ≥ 成本 {cost_threshold}"))

    # C: 量能參考 (僅顯示，不算觸發)
    if avg_vol_5d > 0 and len(volumes) >= 5:
        vol_info = f"5日均量 {avg_vol_5d:.0f} 張 (今日盤中需 ≥{avg_vol_5d*1.5:.0f})"
    else:
        vol_info = None

    # === 第二層：趨勢翻多 (充分) ===
    # D: 5MA > 10MA (黃金交叉後)
    if ma5 and ma10 and ma5 > ma10:
        triggered.append(("D_5MA>10MA", f"5MA {ma5:.2f} > 10MA {ma10:.2f}"))

    # E: RSI > 30 (從超賣回升)
    if rsi and rsi > 30:
        triggered.append(("E_RSI轉強", f"RSI {rsi:.1f} > 30"))

    # F: 現價 > 昨收 (日 K 轉強)
    if len(history) >= 2:
        prev_close = history[1][1]
        if current_price > prev_close:
            triggered.append(("F_日K轉強", f"現價 {current_price} > 昨收 {prev_close}"))

    # === 第三層：結構突破 (強力) ===
    # G: 突破 Buy Zone 中段
    if current_price >= zone_mid:
        triggered.append(("G_突破BuyZone", f"現價 {current_price} ≥ Buy Zone 中段 {zone_mid:.2f}"))

    # H: 站上月線 MA20
    if ma20 and current_price > ma20:
        triggered.append(("H_站上月線", f"現價 {current_price} > MA20 {ma20:.2f}"))

    if not triggered:
        return None

    # 組合推播訊息
    codes_summary = " + ".join([t[0] for t in triggered])
    details_parts = [t[1] for t in triggered[:4]]
    if vol_info:
        details_parts.append(vol_info)
    details = " | ".join(details_parts)

    # 判斷加碼建議
    if any(t[0].startswith(("G_", "H_")) for t in triggered):
        action = "🔴 強力訊號 — 建議加碼至 Buy Zone 中段"
    elif any(t[0].startswith(("D_", "E_", "F_")) for t in triggered):
        action = "🟠 積極訊號 — 建議加碼 2 批"
    elif len([t for t in triggered if t[0].startswith(("A_", "B_", "C_"))]) >= 2:
        action = "🟡 保守訊號 — 建議加碼 1 批"
    else:
        action = f"⚪ 觀察中 — 觸發 {len(triggered)} 個條件，持續追蹤"

    return {
        "type": f"📈 {code} {WATCHLIST.get(code, ('', '', ''))[1]} 反彈訊號",
        "msg": f"{action}\n觸發: {codes_summary}\n{details}"
    }


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

    pairs = get_pairs()
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
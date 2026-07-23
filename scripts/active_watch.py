#!/usr/bin/env python3
"""
Quinn 主動看盤守護員 — 每 10 分鐘盤中監控 (整合庫存)

工作流程：
1. 抓取監控清單的即時報價 (TWSE MIS + TPEx)
2. 從 DB 讀取老大的庫存狀態 (holdings)
3. 根據「有倉/無倉」+ 觸發訊號 (買入價/停損價/目標價) 產生專業建議
4. 透過 Discord 推播給老大 (不重複，每 30 分鐘冷卻)
5. 寫入 logs/intraday-alerts.log 避免重複通知

觸發類型：
- 🟢 進場訊號 (有倉: 加碼, 無倉: 建倉)
- 🚨 停損訊號 (有倉: 停損出場, 無倉: 不動作)
- 🎯 接近目標 (有倉: 考慮減倉, 無倉: 不適用)
- 📉 接近停損 (有倉: 警戒, 無倉: 觀望)
- 📈 突破買區上緣 (有倉: 觀望, 無倉: 進場猶豫期)

使用方式：
  python3 active_watch.py           # 單次執行 (cron 每 10 分鐘呼叫)
  python3 active_watch.py --once    # 同上
  python3 active_watch.py --test    # 測試模式 (不打 Discord)
"""
import csv
import json
import os
import re
import sqlite3
import ssl
import sys
import urllib.parse
import urllib.request
from datetime import datetime, date
from pathlib import Path

# 從統一清單載入
sys.path.insert(0, str(Path(__file__).parent))
from watchlist import WATCHLIST, BUY_ZONES, get_pairs  # noqa: E402

# ========== 設定 ==========
REPO_DIR = Path("/var/repo/tw-stock-research")
DB_PATH = REPO_DIR / "data" / "tw_stock.db"
LOGS_DIR = REPO_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)
ALERT_LOG = LOGS_DIR / "intraday-active-watch.log"

UA = "Mozilla/5.0 (compatible; QuinnActiveWatch/1.0)"
REFERER = "https://mis.twse.com.tw/stock/index.jsp"
TWSE_MIS = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp"


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


def update_intraday_prices(quotes, pairs):
    """將盤中即時報價寫入 DB (供前端顯示)
    - 使用 today 日期
    - 使用 REPLACE 確保同日只保留最新一筆
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        today = date.today().isoformat()
        updated = 0
        for code, (ex, name, market) in pairs:
            m = quotes.get(code)
            if not m:
                continue
            price = get_price(m)
            if price is None:
                continue

            # 讀取前日收盤
            cur.execute("""
                SELECT close FROM price_history
                WHERE ticker=? AND date < ?
                ORDER BY date DESC LIMIT 1
            """, (code, today))
            row = cur.fetchone()
            yclose = row[0] if row else None

            change = (price - yclose) if yclose else None
            change_pct = (change / yclose * 100) if (yclose and change is not None) else None

            # 取得其他欄位
            vol = m.get("v", 0)
            try:
                vol = int(vol)
            except (ValueError, TypeError):
                vol = 0

            cur.execute("""
                INSERT OR REPLACE INTO price_history
                (date, ticker, name, market, close, yclose, change, change_pct, volume_lots, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (today, code, name, market, price, yclose,
                  round(change, 2) if change is not None else None,
                  round(change_pct, 2) if change_pct is not None else None,
                  vol, 'active_watch_intraday'))
            updated += 1
        conn.commit()
        conn.close()
        return updated
    except Exception as e:
        print(f"[更新盤中報價失敗]: {e}")
        return 0


def get_price(m):
    """取得報價 (優先 z, 否則 b, 否則 o)"""
    for key in ["z", "b", "o"]:
        v = m.get(key)
        if v and v not in ("-", "", None):
            try:
                p = float(str(v).split("_")[0])
                if p > 0:
                    return p
            except (ValueError, TypeError):
                pass
    return None


# ========== 庫存讀取 ==========
def get_holdings():
    """從 DB 讀取老大所有庫存 {ticker: {shares, avg_cost}}"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT ticker, shares, avg_cost FROM holdings")
    holdings = {}
    for ticker, shares, avg_cost in cur.fetchall():
        holdings[ticker] = {"shares": shares, "avg_cost": avg_cost}
    conn.close()
    return holdings


# ========== 觸發評估 ==========
def evaluate_stock(code, name, price, zone, holdings):
    """
    根據價格 + 庫存 + Buy Zone 給出建議動作
    Returns: dict 或 None (不觸發)
    """
    if not zone or price is None:
        return None

    buy_min = zone["buy_min"]
    buy_max = zone["buy_max"]
    target = zone["target"]
    stop = zone["stop"]
    rating = zone["rating"]

    holding = holdings.get(code, {"shares": 0, "avg_cost": None})
    shares = holding["shares"]
    has_position = shares > 0
    avg_cost = holding["avg_cost"]

    alerts = []

    # ====== 規則 1: 進入 Buy Zone (未持股) 或 接近加碼區 (有持股) ======
    if price <= buy_min * 1.05:  # buy_min ~ buy_min * 1.05
        if not has_position:
            alerts.append({
                "level": "🟢 強進場訊號",
                "action": "建議建倉",
                "msg": f"現價 {price:.2f} 在 Buy Zone 下緣 ({buy_min}) 內，屬於恐慌低接區",
            })
        else:
            alerts.append({
                "level": "🟢 加碼訊號",
                "action": "建議加碼",
                "msg": f"現價 {price:.2f} 比平均成本 {avg_cost:.2f} {'更低' if price < avg_cost else '接近'}，可加碼攤平",
            })

    elif price <= buy_max:
        if not has_position:
            alerts.append({
                "level": "🟡 中性進場訊號",
                "action": "可考慮小進",
                "msg": f"現價 {price:.2f} 在 Buy Zone 中段 ({buy_min}-{buy_max})",
            })
        # 有持股不觸發 (除非比平均成本低很多)

    # ====== 規則 2: 觸及停損 (僅有持股時) ======
    if stop and price <= stop:
        if has_position:
            alerts.append({
                "level": "🚨 停損訊號",
                "action": "立即停損出場",
                "msg": f"現價 {price:.2f} 已觸及停損價 {stop}，虧損 {(price - avg_cost) / avg_cost * 100:+.1f}%",
            })
        else:
            alerts.append({
                "level": "🛑 觸及停損價 (未持股)",
                "action": "觀望不進",
                "msg": f"現價 {price:.2f} 已觸及停損價 {stop}，但老大未持股，不建議進場",
            })

    # ====== 規則 3: 接近停損 (警戒) ======
    elif stop and price <= stop * 1.05:
        if has_position:
            alerts.append({
                "level": "⚠️ 接近停損",
                "action": "警戒",
                "msg": f"現價 {price:.2f} 距停損 {stop} 僅 {((stop - price) / price * 100):.1f}%，準備停損計畫",
            })

    # ====== 規則 4: 接近目標 (僅有持股時) ======
    if target and price >= target * 0.95:
        if has_position:
            pnl_pct = (price - avg_cost) / avg_cost * 100 if avg_cost else 0
            alerts.append({
                "level": "🎯 接近目標價",
                "action": "考慮減倉",
                "msg": f"現價 {price:.2f} 距目標 {target} 僅 {((target - price) / price * 100):.1f}%，目前獲利 {pnl_pct:+.1f}%",
            })
        # 未持股不觸發

    # ====== 規則 5: 大漲突破 (僅未持股) ======
    if price > buy_max * 1.1:
        if not has_position:
            alerts.append({
                "level": "❌ 突破買區上緣 (未持股)",
                "action": "不追價",
                "msg": f"現價 {price:.2f} 突破 Buy Zone 上緣 {buy_max}，等回檔",
            })

    return alerts if alerts else None


# ========== Discord 推播 ==========
def send_discord(title, body):
    """透過 hermes CLI 推播到 Discord (home channel)"""
    try:
        import subprocess
        full_msg = f"**{title}**\n\n{body}"
        result = subprocess.run(
            ["hermes", "send", "-t", "discord", full_msg],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return True
        print(f"[hermes send stderr]: {result.stderr[:200]}")
        return False
    except FileNotFoundError:
        print("[hermes CLI not found, fallback to log]")
        return False
    except Exception as e:
        print(f"[Discord 推播失敗]: {e}")
        return False


def log_alert(code, alert_type):
    with open(ALERT_LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()}|{code}|{alert_type}\n")


def should_send_recently(code, alert_type, cooldown_min=30):
    """30 分鐘冷卻 (避免重複轟炸)"""
    if not ALERT_LOG.exists():
        return True
    now = datetime.now()
    cutoff = now.timestamp() - cooldown_min * 60
    try:
        with open(ALERT_LOG, encoding="utf-8") as f:
            for line in f:
                try:
                    ts_str, log_code, log_type = line.split("|", 2)
                    ts = datetime.fromisoformat(ts_str)
                    if log_code == code and log_type.strip() == alert_type and ts.timestamp() > cutoff:
                        return False
                except (ValueError, IndexError):
                    continue
    except Exception:
        pass
    return True


# ========== 主程式 ==========
def main():
    test_mode = "--test" in sys.argv

    now = datetime.now()
    # 盤中時間檢查 (09:00-13:30)
    if now.weekday() >= 5:
        print(f"[{now.strftime('%H:%M:%S')}] 週末不執行")
        return 0
    market_open = now.replace(hour=9, minute=0, second=0, microsecond=0)
    market_close = now.replace(hour=13, minute=30, second=0, microsecond=0)
    if now < market_open or now > market_close:
        print(f"[{now.strftime('%H:%M:%S')}] 非盤中時間 ({market_open.strftime('%H:%M')}-{market_close.strftime('%H:%M')})")
        return 0

    print(f"\n[{now.strftime('%H:%M:%S')}] Quinn 主動看盤啟動")
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

    # ✅ 新增: 立即更新盤中報價到 DB (供前端即時顯示)
    updated_count = update_intraday_prices(quotes, pairs)
    print(f"   已更新 DB: {updated_count} 支現價")

    holdings = get_holdings()
    print(f"   庫存: {len(holdings)} 支有倉")

    all_alerts = []
    for code, (ex, name, market) in pairs:
        m = quotes.get(code)
        if not m:
            continue
        price = get_price(m)
        if price is None:
            continue

        zone = BUY_ZONES.get(code)
        if not zone:
            continue

        alerts = evaluate_stock(code, name, price, zone, holdings)
        if not alerts:
            continue

        for alert in alerts:
            all_alerts.append({
                "code": code,
                "name": name,
                "price": price,
                "zone": zone,
                "holding": holdings.get(code, {}),
                "alert": alert,
            })

    if not all_alerts:
        print(f"   ✅ 無觸發訊號 ({len(pairs)} 支監控中)")
        return 0

    # 過濾冷卻時間
    new_alerts = []
    for a in all_alerts:
        atype = a["alert"]["level"]
        # 過濾「中性進場」訊號 (太吵) — 改為只在強進場/停損/接近目標/接近停損時推播
        if "中性進場" in atype:
            continue
        if test_mode or should_send_recently(a["code"], atype):
            new_alerts.append(a)
            log_alert(a["code"], atype)

    print(f"\n🔔 觸發 {len(all_alerts)} 個訊號 (新推播 {len(new_alerts)} 個)")

    if not new_alerts or test_mode:
        for a in all_alerts:
            print(f"  {a['code']} {a['name']} {a['price']:.2f}: {a['alert']['level']}")
        return 0

    # 組合 Discord 訊息
    msg_lines = [f"⏰ **{now.strftime('%H:%M')} 盤中監控**", ""]
    for a in new_alerts:
        z = a["zone"]
        h = a["holding"]
        upside = ((z["target"] - a["price"]) / a["price"] * 100) if z.get("target") else 0

        # 庫存狀態標記
        pos_status = f"📦 已持 {h.get('shares', 0):,} 股 @ {h.get('avg_cost', 0):.2f}" if h.get("shares", 0) > 0 else "📭 未持股"

        msg_lines.append(
            f"**{a['code']} {a['name']}** — {a['price']:.2f}\n"
            f"  • 訊號: {a['alert']['level']}\n"
            f"  • 動作: {a['alert']['action']}\n"
            f"  • 庫存: {pos_status}\n"
            f"  • 評等: {z.get('rating', '-')}\n"
            f"  • {a['alert']['msg']}\n"
            f"  • Buy Zone: {z['buy_min']:.1f}–{z['buy_max']:.1f} | 目標 {z.get('target', '-'):.1f} ({upside:+.1f}%) | 停損 {z.get('stop') or '-'}\n"
        )

    msg_lines.append("─" * 30)
    msg_lines.append("💡 回應方式：\n• 輸入「已下單」+ 標的股數價格\n• 輸入「觀望」跳過\n• 輸入「停損」確認出場")

    body = "\n".join(msg_lines)
    print(f"\n[準備推播]\n{body[:500]}...")

    if send_discord("🔔 Quinn 盤中監控", body):
        print("✅ Discord 通知已送出")
    else:
        print("⚠️ Discord 推播失敗 (請檢查 hermes_tools)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
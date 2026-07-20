#!/usr/bin/env python3
"""
台股每日收盤價記錄工具 — Quinn 投資分析師專用

功能：
1. 抓取監控清單的即時報價 (TWSE MIS API)
2. 抓取殖利率、本益比 (上市 BWIBBU / 上櫃 TPEx)
3. 寫入 CSV 歷史檔 (供未來技術分析)

使用方式：
  python3 fetch_prices.py              # 抓全部 WATCHLIST (預設 8 支)
  python3 fetch_prices.py 2330 2317    # 抓指定股票
"""

import json
import csv
import sys
import os
from datetime import datetime, date
from pathlib import Path
import urllib.request
import urllib.parse
import ssl

# 從統一清單載入
sys.path.insert(0, str(Path(__file__).parent))
from watchlist import WATCHLIST, get_pairs  # noqa: E402

# ========== 設定 ==========
REPO_DIR = Path("/var/repo/tw-stock-research")
HISTORY_DIR = REPO_DIR / "price-history"
HISTORY_DIR.mkdir(exist_ok=True)

# 統一監控清單 — 從 watchlist.py 載入 (Single Source of Truth)
# 詳見 watchlist.py 註解說明

UA = "Mozilla/5.0 (compatible; QuinnStockBot/1.0)"
REFERER = "https://mis.twse.com.tw/stock/index.jsp"
TWSE_MIS = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp"
BWIBBU_ALL = "https://openapi.twse.com.tw/v1/exchangeReport/BWIBBU_ALL"
TPEX_PERATIO = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_peratio_analysis"

# ========== 工具函式 ==========
def http_get(url, timeout=20):
    req = urllib.request.Request(url)
    req.add_header("User-Agent", UA)
    req.add_header("Referer", REFERER)
    req.add_header("Accept", "*/*")
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        return r.read().decode("utf-8")


def build_ex_ch(pairs):
    """建立 TWSE MIS API 的 ex_ch 參數 (上市 tse_xxx.tw | 上櫃 otc_xxx.tw)"""
    chs = []
    for code, (ex, _, _) in pairs:
        if ex == "tse":
            chs.append(f"tse_{code}.tw")
        elif ex == "otc":
            chs.append(f"otc_{code}.tw")
    return "|".join(chs)


def fetch_quote(pairs):
    """抓即時報價"""
    if not pairs:
        return {}
    ex_ch = build_ex_ch(pairs)
    url = f"{TWSE_MIS}?json=1&delay=0&ex_ch={urllib.parse.quote(ex_ch)}"
    raw = http_get(url)
    data = json.loads(raw)
    out = {}
    for m in data.get("msgArray", []):
        code = m.get("c")
        if code:
            out[code] = m
    return out


def _positive_number(value):
    """將 MIS 欄位正規化為正數；'-'、空值、0 均視為無效。"""
    try:
        number = float(value)
        return number if number > 0 else None
    except (TypeError, ValueError):
        return None


def normalized_price(message):
    """優先取最新成交；無成交時取最佳買一估算，避免虛構 -100%。"""
    last = _positive_number(message.get("z"))
    if last is not None:
        return last, "last"
    best_bid = _positive_number((message.get("b") or "").split("_")[0])
    if best_bid is not None:
        return best_bid, "best_bid_estimate"
    indicative = _positive_number(message.get("o")) or _positive_number(message.get("l"))
    if indicative is not None:
        return indicative, "indicative_ohlc"
    return None, "unavailable"


def fetch_bwibbu():
    """抓上市股殖利率 / 本益比 / 股價淨值比"""
    try:
        raw = http_get(BWIBBU_ALL)
        data = json.loads(raw)
        out = {}
        for row in data:
            code = row.get("Code") or row.get("證券代號", "")
            if code:
                out[code] = {
                    "pe": row.get("PEratio") or row.get("本益比", ""),
                    "pb": row.get("PBratio") or row.get("股價淨值比", ""),
                    "yield": row.get("DividendYield") or row.get("殖利率(%)", ""),
                }
        return out
    except Exception as e:
        print(f"[WARN] TWSE BWIBBU fetch failed: {e}")
        return {}


def fetch_tpex_peratio():
    """抓上櫃股殖利率 / 本益比 / 股價淨值比"""
    try:
        raw = http_get(TPEX_PERATIO)
        data = json.loads(raw)
        out = {}
        items = data if isinstance(data, list) else []
        for row in items:
            code = (row.get("SecuritiesCompanyCode") or row.get("Code") or "").strip()
            if code:
                out[code] = {
                    "pe": row.get("PriceEarningRatio", ""),
                    "pb": row.get("PriceBookRatio", ""),
                    "yield": row.get("YieldRatio", ""),
                }
        return out
    except Exception as e:
        print(f"[WARN] TPEx PERATIO fetch failed: {e}")
        return {}


def get_market_status():
    """判斷是否收盤 (簡化版：平日 13:30 之後視為收盤)"""
    now = datetime.now()
    if now.weekday() >= 5:  # 週六日
        return "closed_weekend"
    market_close = now.replace(hour=13, minute=30, second=0, microsecond=0)
    if now < market_close:
        return "trading"
    return "closed"


# ========== 主程式 ==========
def main():
    # 解析 CLI 參數
    # (預設) 抓全部 WATCHLIST (8 支)
    # [codes...] 指定特定股票
    if len(sys.argv) > 1:
        custom_codes = sys.argv[1:]
        pairs = []
        for code in custom_codes:
            code = code.strip()
            if code in WATCHLIST:
                ex, name, market = WATCHLIST[code]
                pairs.append((code, (ex, name, market)))
            else:
                # 預設上市
                pairs.append((code, ("tse", "?", "?")))
    else:
        pairs = get_pairs()

    print(f"📊 Quinn 收盤價記錄器 (機械抓取 — 純資料, 無分析)")
    print(f"   監控標的: {len(pairs)} 支")
    print(f"   當下時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   市場狀態: {get_market_status()}")
    print()

    # 抓報價
    quotes = fetch_quote(pairs)
    if not quotes:
        print("❌ 無法取得報價 (API 失敗)")
        return 1

    # 抓殖利率/本益比 (上市 + 上櫃)
    bwibbu = fetch_bwibbu()
    tpex_peratio = fetch_tpex_peratio()

    # 整理資料
    today = date.today().isoformat()
    rows = []
    fallback_codes = []
    print(f"{'代碼':<6} {'名稱':<10} {'成交':>8} {'昨收':>8} {'漲跌':>7} {'漲跌幅':>7} {'成交量':>10} {'PE':>6} {'殖利率':>7}")
    print("-" * 85)

    for code, (ex, name, market) in pairs:
        m = quotes.get(code)
        if not m:
            print(f"{code} {name}: 無報價資料")
            continue

        price_f, quote_source = normalized_price(m)
        yclose_f = _positive_number(m.get("y"))
        if quote_source != "last":
            fallback_codes.append((code, quote_source))
        if price_f is not None and yclose_f is not None:
            change = price_f - yclose_f
            change_pct = change / yclose_f * 100
        else:
            change = None
            change_pct = None

        vol = m.get("v", "0")
        # 上市用 TWSE BWIBBU，上櫃用 TPEx
        if ex == "tse":
            bw = bwibbu.get(code, {})
        else:
            bw = tpex_peratio.get(code, {})
        pe = bw.get("pe", "-")
        yld = bw.get("yield", "-")

        # 處理 None 顯示
        p_str = f"{price_f:>8.2f}" if price_f is not None else "       -"
        y_str = f"{yclose_f:>8.2f}" if yclose_f is not None else "       -"
        c_str = f"{change:>+7.2f}" if change is not None else "     -"
        cp_str = f"{change_pct:>+6.2f}%" if change_pct is not None else "    -%"

        print(f"{code:<6} {name:<10} {p_str} {y_str} {c_str} {cp_str} {vol:>10} {str(pe):>6} {str(yld):>7}")

        rows.append({
            "date": today,
            "code": code,
            "name": name,
            "market": market,
            "open": m.get("o", "") if m.get("o") not in ("-", "") else None,
            "high": m.get("h", "") if m.get("h") not in ("-", "") else None,
            "low": m.get("l", "") if m.get("l") not in ("-", "") else None,
            "close": price_f,
            "yclose": yclose_f,
            "change": round(change, 3) if change is not None else None,
            "change_pct": round(change_pct, 3) if change_pct is not None else None,
            "volume_lots": vol,
            "pe": pe,
            "yield_pct": yld,
        })

    # 寫入歷史 CSV (append 模式)
    csv_file = HISTORY_DIR / "daily-prices.csv"
    write_header = not csv_file.exists()
    with open(csv_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        if write_header:
            writer.writeheader()
        writer.writerows(rows)

    # 同步寫入 SQLite (給 web 顯示用)
    try:
        import sqlite3
        db_path = REPO_DIR / "data" / "tw_stock.db"
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        for r in rows:
            # 用 INSERT OR REPLACE 避免重複
            cur.execute("""
                INSERT OR REPLACE INTO price_history
                (date, ticker, name, market, open, high, low, close, yclose, change, change_pct, volume_lots, pe, yield_pct, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                r["date"], r["code"], r["name"], r["market"],
                r["open"], r["high"], r["low"],
                r["close"], r["yclose"],
                r["change"], r["change_pct"],
                r["volume_lots"], r["pe"], r["yield_pct"],
                "fetch_prices.py"
            ))
        conn.commit()
        conn.close()
        print(f"✅ SQLite 同步寫入: {db_path}")
    except Exception as e:
        print(f"⚠️ SQLite 寫入失敗 (CSV 仍可用): {e}")

    print()
    if fallback_codes:
        details = ", ".join(f"{code}:{source}" for code, source in fallback_codes)
        print(f"⚠️ z 無最新成交者採最佳買一／OHLC 估算：{details}")
        print("   執行以券商即時成交為準；無有效價格者不計算漲跌幅。")
    print(f"✅ 歷史記錄已寫入: {csv_file}")
    print(f"   總筆數: {sum(1 for _ in csv_file.open())} (含表頭)")

    return 0


if __name__ == "__main__":
    sys.exit(main())

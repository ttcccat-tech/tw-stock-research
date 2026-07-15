#!/usr/bin/env python3
"""
台股每日收盤價記錄工具 — Quinn 投資分析師專用

功能：
1. 抓取監控清單的即時報價 (TWSE MIS API)
2. 抓取殖利率、本益比 (BWIBBU API)
3. 寫入 CSV 歷史檔 (供未來技術分析)

使用方式：
  python3 fetch_prices.py              # 抓取 4 支監控股
  python3 fetch_prices.py 2330 2317    # 抓取指定股票
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

# ========== 設定 ==========
REPO_DIR = Path("/var/repo/tw-stock-research")
HISTORY_DIR = REPO_DIR / "price-history"
HISTORY_DIR.mkdir(exist_ok=True)

# 監控清單 (上市 tse / 上櫃 otc)
WATCHLIST = {
    # ticker: (exchange, name, market)
    "2753": ("tse", "八方雲集", "上市"),
    "1734": ("tse", "杏輝", "上市"),
    "6509": ("otc", "聚和國際", "上櫃"),
    "2834": ("tse", "臺企銀", "上市"),
}

# AI 概念股候選 (用 add_watchlist 動態加入)
AI_WATCHLIST = {
    # 邊緣運算 + IPC (優先)
    "3416": ("tse", "融程電", "上市"),
    "3479": ("otc", "安勤", "上櫃"),
    "3022": ("tse", "威強電", "上市"),
    "8234": ("tse", "新漢", "上市"),
    "6414": ("tse", "樺漢", "上市"),
    # 矽光子 / CPO
    "2455": ("tse", "全新", "上市"),
    "3163": ("otc", "波若威", "上櫃"),
    "3363": ("otc", "上詮", "上櫃"),
    "3081": ("otc", "聯亞", "上櫃"),
    "4977": ("tse", "眾達-KY", "上市"),
    # AI 散熱
    "8088": ("otc", "艾姆勒", "上櫃"),
    "6805": ("tse", "富世達", "上市"),
    "3483": ("tse", "力致", "上市"),
    "3071": ("tse", "協禧", "上市"),
    # AI 電源
    "4931": ("tse", "新盛力", "上市"),
    "3015": ("tse", "全漢", "上市"),
    "8109": ("tse", "博大", "上市"),
    "6412": ("tse", "群電", "上市"),
}

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
    # --ai: 抓 AI 候選股
    # --all: 抓全部 (4 主監控 + 18 AI 候選)
    # 否則只抓主監控
    if "--all" in sys.argv:
        watchlist = {**WATCHLIST, **AI_WATCHLIST}
        sys.argv.remove("--all")
    elif "--ai" in sys.argv:
        watchlist = AI_WATCHLIST
        sys.argv.remove("--ai")
    else:
        watchlist = WATCHLIST

    if len(sys.argv) > 1:
        custom_codes = sys.argv[1:]
        pairs = []
        for code in custom_codes:
            code = code.strip()
            if code in watchlist:
                ex, name, market = watchlist[code]
                pairs.append((code, (ex, name, market)))
            else:
                # 預設上市
                pairs.append((code, ("tse", "?", "?")))
    else:
        pairs = [(code, info) for code, info in watchlist.items()]

    print(f"📊 Quinn 收盤價記錄器")
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
    print(f"{'代碼':<6} {'名稱':<10} {'成交':>8} {'昨收':>8} {'漲跌':>7} {'漲跌幅':>7} {'成交量':>10} {'PE':>6} {'殖利率':>7}")
    print("-" * 85)

    for code, (ex, name, market) in pairs:
        m = quotes.get(code)
        if not m:
            print(f"{code} {name}: 無報價資料")
            continue

        price = m.get("z") or m.get("b") or "0"  # 成交價 / 買價
        yclose = m.get("y", "0")
        try:
            price_f = float(price) if price not in ("-", "", None) else 0
            yclose_f = float(yclose) if yclose not in ("-", "", None) else 0
            change = price_f - yclose_f
            change_pct = (change / yclose_f * 100) if yclose_f else 0
        except (ValueError, TypeError):
            price_f = yclose_f = change = change_pct = 0

        vol = m.get("v", "0")
        # 上市用 TWSE BWIBBU，上櫃用 TPEx
        if ex == "tse":
            bw = bwibbu.get(code, {})
        else:
            bw = tpex_peratio.get(code, {})
        pe = bw.get("pe", "-")
        yld = bw.get("yield", "-")

        print(f"{code:<6} {name:<10} {price_f:>8.2f} {yclose_f:>8.2f} {change:>+7.2f} {change_pct:>+6.2f}% {vol:>10} {str(pe):>6} {str(yld):>7}")

        rows.append({
            "date": today,
            "code": code,
            "name": name,
            "market": market,
            "open": m.get("o", ""),
            "high": m.get("h", ""),
            "low": m.get("l", ""),
            "close": price_f,
            "yclose": yclose_f,
            "change": round(change, 3),
            "change_pct": round(change_pct, 3),
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

    print()
    print(f"✅ 歷史記錄已寫入: {csv_file}")
    print(f"   總筆數: {sum(1 for _ in csv_file.open())} (含表頭)")

    return 0


if __name__ == "__main__":
    sys.exit(main())

# Quinn Stock Watchlist — 統一監控清單 (Single Source of Truth)
#
# ⚠️ 新增標的時，請只改這個檔。fetch_prices.py 和 intraday_monitor.py 都會自動讀取。
#
# 格式: "ticker": ("exchange", "name", "market")
#   - exchange: "tse" 上市 / "otc" 上櫃
#   - market: 顯示用
WATCHLIST = {
    # ticker: (exchange, name, market)
    # === 主監控 (原 4 支) ===
    "2753": ("tse", "八方雲集", "上市"),
    "1734": ("tse", "杏輝", "上市"),
    "6509": ("otc", "聚和國際", "上櫃"),
    "2834": ("tse", "臺企銀", "上市"),
    # === AI 候選 (Quinn 親選 4 支) ===
    "3479": ("tse", "安勤", "上市"),
    "6412": ("tse", "群電", "上市"),
    "2241": ("tse", "艾姆勒", "上市"),
    "4977": ("tse", "眾達-KY", "上市"),
    # === 老大 2026-07-16 新加入的 3 支 ===
    "6472": ("tse", "保瑞", "上市"),
    "6409": ("tse", "旭隼", "上市"),  # ⚠️ 修正：原誤寫 4540
    "6515": ("tse", "穎崴", "上市"),
}

# 進場區間 (從各 reports/*.md 的「交易決策框架」擷取)
# 格式: ticker -> {'buy_min': 積極進場下緣, 'buy_max': 保守進場上緣, 'target': 目標價, 'stop': 停損價, 'rating': 評等}
BUY_ZONES = {
    "2753": {"buy_min": 145.0, "buy_max": 200.0, "target": 235.0, "stop": 150.0, "rating": "Hold"},
    "1734": {"buy_min": 30.0, "buy_max": 34.0, "target": 40.0, "stop": 28.0, "rating": "Buy"},   # 杏輝 (下修, 杏國拖累)
    "6509": {"buy_min": 42.0, "buy_max": 50.0, "target": 55.0, "stop": 40.0, "rating": "Buy"},   # 聚和 (下修, 2026/7 因月營收警訊)
    "2834": {"buy_min": 14.0, "buy_max": 17.5, "target": 19.0, "stop": None, "rating": "Buy (存股)"},
    "3479": {"buy_min": 115.0, "buy_max": 160.0, "target": 165.0, "stop": 115.0, "rating": "Watch"},
    "6412": {"buy_min": 75.0, "buy_max": 100.0, "target": 100.0, "stop": None, "rating": "Buy (存股)"},
    "2241": {"buy_min": 42.0, "buy_max": 70.0, "target": 85.0, "stop": 42.0, "rating": "Buy 爆發型"},
    "4977": {"buy_min": 120.0, "buy_max": 200.0, "target": 220.0, "stop": 120.0, "rating": "Buy 核心持股"},
    # === 新加入 3 支 (Quinn 校正後) ===
    "6472": {"buy_min": 380.0, "buy_max": 470.0, "target": 580.0, "stop": 365.0, "rating": "Buy"},   # 保瑞
    "6409": {"buy_min": 950.0, "buy_max": 1100.0, "target": 1400.0, "stop": 900.0, "rating": "Buy"}, # 旭隼 (千金股)
    "6515": {"buy_min": 5500.0, "buy_max": 7500.0, "target": 9000.0, "stop": 5200.0, "rating": "Buy 核心持股"},  # 穎崴 (千金股)
}


def get_all_codes():
    """回傳所有監控標的代碼 (供 fetch_prices / intraday_monitor 使用)"""
    return list(WATCHLIST.keys())


def get_pairs():
    """回傳 (code, info) 的 list"""
    return [(code, info) for code, info in WATCHLIST.items()]


def get_zone(code):
    """取得單一股票的進場區間"""
    return BUY_ZONES.get(code)


# ==========================================================
# Quinn 主動選股顧問 — 觀察池 (Scan Pool)
# ==========================================================
# 觀察池是 Quinn 主動追蹤但尚未建議老大加入的候選股
# 達標 (>75) → 自動建議加入; 惡化 (<50) → 自動建議移除
#
# 結構: code -> {exchange, name, market, theme, added_at, note}
# SCAN_STATUS: code -> "NEW" | "EVALUATING" | "WATCH" | "RECOMMEND_ADD" | "RECOMMEND_REMOVE" | "ARCHIVED"

SCAN_WATCHLIST = {
    # === 半導體/AI 設備次族群 ===
    "6515": {"exchange": "tse", "name": "穎崴",   "market": "上市", "theme": "AI 測試介面", "added_at": "2026-07-16", "note": "AI 晶片 probe card 受惠輝達 Blackwell", "status": "ACCEPTED"},
    "6409": {"exchange": "tse", "name": "旭隼",   "market": "上市", "theme": "AI 電源 (UPS)", "added_at": "2026-07-16", "note": "全球前三 AI 機房 UPS 廠，800V DC 合作", "status": "ACCEPTED"},
    "3131": {"exchange": "tse", "name": "弘塑",   "market": "上市", "theme": "CoWoS 封測", "added_at": "2026-07-16", "note": "先進封裝設備", "status": "EVALUATING"},
    "3583": {"exchange": "tse", "name": "辛耘",   "market": "上市", "theme": "半導體設備", "added_at": "2026-07-16", "note": "晶圓濕製程設備", "status": "EVALUATING"},
    "6187": {"exchange": "tse", "name": "萬潤",   "market": "上市", "theme": "CoWoS 設備", "added_at": "2026-07-16", "note": "封測自動化設備", "status": "EVALUATING"},
    "5309": {"exchange": "tse", "name": "系統電", "market": "上市", "theme": "工業電腦", "added_at": "2026-07-16", "note": "IPC 次族群", "status": "NEW"},
    "6224": {"exchange": "tse", "name": "聚鼎",   "market": "上市", "theme": "散熱元件", "added_at": "2026-07-16", "note": "高分子散熱", "status": "NEW"},
    # === 生技/醫材 ===
    "6472": {"exchange": "tse", "name": "保瑞",     "market": "上市", "theme": "CDMO/學名藥", "added_at": "2026-07-16", "note": "2024 收購 Upsher-Smith", "status": "ACCEPTED"},
    "6446": {"exchange": "tse", "name": "藥華藥",   "market": "上市", "theme": "新藥 (P1101)", "added_at": "2026-07-16", "note": "罕病藥、減肥藥海外授權"},
    "4147": {"exchange": "tse", "name": "中裕",     "market": "上市", "theme": "愛滋新藥", "added_at": "2026-07-16", "note": "Trogarzo 已上市"},
    "4123": {"exchange": "tse", "name": "晟德",     "market": "上市", "theme": "生技控股", "added_at": "2026-07-16", "note": "轉投資多家高潛力公司"},
    # === 金融/壽險 (民營金控) ===
    "2891": {"exchange": "tse", "name": "中信金",   "market": "上市", "theme": "民營金控", "added_at": "2026-07-16", "note": "民營金控獲利王"},
    "2884": {"exchange": "tse", "name": "玉山金",   "market": "上市", "theme": "民營金控", "added_at": "2026-07-16", "note": "海外布局完整"},
    "2885": {"exchange": "tse", "name": "元大金",   "market": "上市", "theme": "民營金控", "added_at": "2026-07-16", "note": "證券業務領先"},
    "2882": {"exchange": "tse", "name": "國泰金",   "market": "上市", "theme": "民營金控", "added_at": "2026-07-16", "note": "壽險 + 國泰世華銀"},
    # === 傳產/景氣循環 ===
    "2603": {"exchange": "tse", "name": "長榮",     "market": "上市", "theme": "航運", "added_at": "2026-07-16", "note": "貨櫃三雄, 受惠運價"},
    "2609": {"exchange": "tse", "name": "陽明",     "market": "上市", "theme": "航運", "added_at": "2026-07-16", "note": "貨櫃三雄"},
    "1301": {"exchange": "tse", "name": "台塑",     "market": "上市", "theme": "石化", "added_at": "2026-07-16", "note": "塑化龍頭"},
    "1303": {"exchange": "tse", "name": "南亞",     "market": "上市", "theme": "石化/電子", "added_at": "2026-07-16", "note": "石化 + PCB"},
    # === ETF ===
    "0050": {"exchange": "tse", "name": "元大台灣50", "market": "上市", "theme": "ETF 大盤", "added_at": "2026-07-16", "note": "跟大盤"},
    "0056": {"exchange": "tse", "name": "元大高股息", "market": "上市", "theme": "高股息 ETF", "added_at": "2026-07-16", "note": "存股族最愛"},
    "00878": {"exchange": "tse", "name": "國泰永續高股息", "market": "上市", "theme": "高股息 ETF", "added_at": "2026-07-16", "note": "新興高股息"},
}

# 觀察池狀態 (Quinn 追蹤用)
# 2026-07-16 更新：老大已接受 3 支 (6472/4540/6515) 進主清單
SCAN_STATUS = {
    # === 已轉主清單 (老大 2026-07-16 接受) ===
    "6472": "ARCHIVED_TRANSFERRED",  # → 主清單
    "4540": "ARCHIVED_TRANSFERRED",  # → 主清單
    "6515": "ARCHIVED_TRANSFERRED",  # → 主清單
    # === 達標待 8/1 月度提案 (2026-07-19 週報評估) ===
    "6446": "RECOMMEND_ADD",     # 藥華藥 - 評分 80, 達標
    "3131": "RECOMMEND_ADD",     # 弘塑 - 評分 78, 達標
    "3583": "RECOMMEND_ADD",     # 辛耘 - 評分 76, 達標
    "6187": "RECOMMEND_ADD",     # 萬潤 - 評分 75, 達標
    "2891": "RECOMMEND_ADD",     # 中信金 - 評分 76, 達標
    # === 持續 WATCH ===
    "4123": "WATCH",       # 晟德
    # === 繼續 EVALUATING ===
    "4147": "EVALUATING",  # 中裕
    "5309": "NEW",         # 系統電
    "6224": "NEW",         # 聚鼎
    "2884": "EVALUATING",  # 玉山金
    "2885": "EVALUATING",  # 元大金
    "2882": "EVALUATING",  # 國泰金
    "2603": "EVALUATING",  # 長榮
    "2609": "EVALUATING",  # 陽明
    "1301": "EVALUATING",  # 台塑
    "1303": "EVALUATING",  # 南亞
    "0050": "NEW",         # ETF 大盤
    "0056": "NEW",         # ETF 高股息
    "00878": "NEW",        # ETF 高股息
}


def add_scan(code, exchange, name, market, theme, note=""):
    """新增觀察池標的 (主動提案用)"""
    SCAN_WATCHLIST[code] = {
        "exchange": exchange,
        "name": name,
        "market": market,
        "theme": theme,
        "added_at": datetime.now().strftime("%Y-%m-%d"),
        "note": note,
    }
    SCAN_STATUS[code] = "NEW"


def add_main(code, exchange, name, market, buy_min, buy_max, target, stop, rating, theme=""):
    """新增主清單標的 (接受提案時呼叫)"""
    WATCHLIST[code] = (exchange, name, market)
    BUY_ZONES[code] = {
        "name": name,
        "buy_min": buy_min,
        "buy_max": buy_max,
        "target": target,
        "stop": stop,
        "rating": rating,
    }
    # 從觀察池移到 ARCHIVED
    SCAN_STATUS[code] = "ARCHIVED"


def remove_main(code, reason=""):
    """移除主清單標的 (建議移除時呼叫)"""
    if code in WATCHLIST:
        del WATCHLIST[code]
    if code in BUY_ZONES:
        del BUY_ZONES[code]
    print(f"  🔴 已移除 {code} from main list. Reason: {reason}")


from datetime import datetime


if __name__ == "__main__":
    # CLI 測試
    import sys
    if "--list" in sys.argv:
        print(f"📊 Quinn 監控清單 (共 {len(WATCHLIST)} 支)")
        print()
        for code, info in WATCHLIST.items():
            zone = BUY_ZONES.get(code, {})
            print(f"  {code} {info[1]} ({info[2]}) | 評等 {zone.get('rating', '-')}")
            print(f"      進場 {zone.get('buy_min')}-{zone.get('buy_max')} → 目標 {zone.get('target')} | 停損 {zone.get('stop') or 'N/A (存股)'}")
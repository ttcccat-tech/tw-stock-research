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
    "3479": ("otc", "安勤", "上櫃"),
    "6412": ("tse", "群電", "上市"),
    # 2241 艾姆勒 — 2026-08-09 週報決議從主清單移除（8/5 Q2 財報 H1 虧損 4,366 萬、Q2 EPS -0.27、毛利率 7.67%；8/7 -6.98% 跌破停損；出清待券商實際回報）
    "4977": ("tse", "眾達-KY", "上市"),
    # 2241 艾姆勒 — 2026-08-10 老大決議保留 2,000 股 @ 34.75 (覆蓋 8/9 移除決議)
    # 觀察價 36-38 (反彈高點提示) / 停損 30 (強制檢視) / 34-38 區間不通知
    "2241": ("tse", "艾姆勒", "上市"),  # 2026-08-18 修正：MIS pid 顯示為 tse (上市) 非 otc
    # === 老大 2026-07-16 新加入的 3 支 ===
    "6472": ("tse", "保瑞", "上市"),
    "6409": ("tse", "旭隼", "上市"),  # ⚠️ 修正：原誤寫 4540
    "6515": ("tse", "穎崴", "上市"),
    # === 老大 2026-07-23 新加入 (存股觀察) ===
    "2330": ("tse", "台積電", "上市"),  # 🆕 存股核心，Buy Zone 用殖利率法
    # === 老大 2026-08-10 新加入 (民生消費通路王) ===
    "5904": ("otc", "寶雅*", "上櫃"),  # 🆕 居家生活通路王，1 拆 10 後基本面 +34.7% 🚀
    # === 老大 2026-08-10 加入主清單 (基本面 vs 技術面脫鉤戰術) ===
    "7780": ("tse", "大研生醫*", "上市"),  # 🆕 保健食品王，庫藏區下限 12.75 保護，分 3 批進場 (B 計畫) (2026-08-18 修正：MIS pid 顯示為 tse)
}

# 進場區間 (從各 reports/*.md 的「交易決策框架」擷取)
# 格式: ticker -> {'buy_min': 積極進場下緣, 'buy_max': 保守進場上緣, 'target': 目標價, 'stop': 停損價, 'rating': 評等}
BUY_ZONES = {
    "2753": {"buy_min": 145.0, "buy_max": 200.0, "target": 235.0, "stop": 150.0, "rating": "Hold"},
    "1734": {"buy_min": 30.0, "buy_max": 34.0, "target": 40.0, "stop": 28.0, "rating": "Buy"},   # 杏輝 (下修, 杏國拖累)
    "6509": {"buy_min": 45.0, "buy_max": 55.0, "target": 60.0, "stop": 42.0, "rating": "Buy"},   # 聚和 (2026-08-09 週報更新：7 月營收 +7.28% 連 2 月年增、Buy Zone 突破；主清單評分 72→75；可於 46-48 加碼 1,000 股)
    "2834": {"buy_min": 14.0, "buy_max": 17.5, "target": 19.0, "stop": None, "rating": "Buy (存股)"},
    "3479": {"buy_min": 115.0, "buy_max": 160.0, "target": 165.0, "stop": 115.0, "rating": "Watch"},
    "6412": {"buy_min": 75.0, "buy_max": 100.0, "target": 100.0, "stop": None, "rating": "Buy (存股)"},
    # 2241 艾姆勒 — 2026-08-10 老大決議保留 2,000 股 @ 34.75
    # buy_min=0/buy_max=0 → 跳過進場訊號 (保留狀態) ; target=38 觀察高點 ; stop=30 強制檢視
    "2241": {"buy_min": 0.0, "buy_max": 0.0, "target": 38.0, "stop": 30.0, "rating": "Hold 保留中"},
    "4977": {"buy_min": 120.0, "buy_max": 200.0, "target": 220.0, "stop": 120.0, "rating": "Buy 核心持股"},
    # === 新加入 3 支 (Quinn 校正後) ===
    "6472": {"buy_min": 380.0, "buy_max": 470.0, "target": 580.0, "stop": 365.0, "rating": "Buy"},   # 保瑞 — 2026-08-23 週報: 8/20 漲停結構翻多確認, 升評 65→68; 不追 455; 回 430-445 兩日不破才小倉 3-5%
    "6409": {"buy_min": 950.0, "buy_max": 1100.0, "target": 1400.0, "stop": 900.0, "rating": "Buy"}, # 旭隼 (千金股)
    "6515": {"buy_min": 5500.0, "buy_max": 7500.0, "target": 9000.0, "stop": 5200.0, "rating": "Buy 核心持股"},  # 穎崴 (千金股)
    # === 台積電 (存股觀察) — 殖利率法估算 ===
    # EPS 50-60 元 (2026 市場預估中位數)
    # 殖利率 3% → 1,670-2,000 (積極進場)
    # 殖利率 2.5% → 2,000-2,400 (中性進場)
    # 殖利率 2% → 2,500-3,000 (保守進場 / 等回檔)
    "2330": {"buy_min": 1670.0, "buy_max": 2400.0, "target": 3000.0, "stop": 1500.0, "rating": "Buy 存股核心"},  # 台積電 — 殖利率 2-3% 區間進場
    # === 寶雅* (5904) — 拆股後 (1 拆 10) ===
    # EPS 8.15 (Q2) / 17.45 (H1) / YoY +34.7% / 毛利率 44.94% (史高) / 營益率 15.40% (史高)
    # 法人目標價 80 (拆股後，原 800) / Buy Zone 72-75 (拆股後參考價)
    "5904": {"buy_min": 60.0, "buy_max": 75.0, "target": 90.0, "stop": 70.0, "rating": "Buy 核心持股"},  # 寶雅* — 通路王分批進場
    # === 大研生醫* (7780) — 老大 B 計畫分 3 批 ===
    # 第 1 批 (30%): 15.5-16 元 恐慌試單
    # 第 2 批 (40%): 12.75-13.5 元 庫藏區下限加碼
    # 第 3 批 (30%): 17.5-18 元 突破月線滿足
    # 目標 25 / 停損 11.5 (跌破庫藏區下限)
    # 風險報酬比 3.5x
    "7780": {"buy_min": 12.75, "buy_max": 16.0, "target": 25.0, "stop": 11.5, "rating": "Buy (分批 30/40/30)"},  # 大研生醫* — B 計畫脫鉤套利
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
    # 2026-08-30 週報：4977 升評 64→70 (8/26 漲停 +10%, 本週 +14.29%, 結構翻多確認)
    "4977": {"exchange": "tse", "name": "眾達-KY", "market": "上市", "theme": "光通訊/CPO", "added_at": "2026-08-30", "note": "2026-08-30 週報升評 64→70；8/26 漲停 +10%；本週 +14.29%；CPO + 品固雙引擎確認", "status": "ACCEPTED"},
    "3131": {"exchange": "tse", "name": "弘塑",   "market": "上市", "theme": "CoWoS 封測", "added_at": "2026-07-16", "note": "先進封裝設備", "status": "EVALUATING"},
    "3583": {"exchange": "tse", "name": "辛耘",   "market": "上市", "theme": "半導體設備", "added_at": "2026-07-16", "note": "晶圓濕製程設備", "status": "EVALUATING"},
    "6187": {"exchange": "tse", "name": "萬潤",   "market": "上市", "theme": "CoWoS 設備", "added_at": "2026-07-16", "note": "封測自動化設備", "status": "EVALUATING"},
    "5309": {"exchange": "tse", "name": "系統電", "market": "上市", "theme": "工業電腦", "added_at": "2026-07-16", "note": "IPC 次族群", "status": "NEW"},
    "6224": {"exchange": "tse", "name": "聚鼎",   "market": "上市", "theme": "散熱元件", "added_at": "2026-07-16", "note": "高分子散熱", "status": "NEW"},
    "3008": {"exchange": "tse", "name": "大立光", "market": "上市", "theme": "手機鏡頭/車用光學", "added_at": "2026-08-02", "note": "2026-08-30 週報連續 3 週提案；7 月營收 54.13 億月增+31% 寫今年新高；法說會看好 8 月拉貨；Q1 EPS 46.63 / 毛利率 49.41%；CPO 試產線 9 月啟動；評分 79", "status": "RECOMMEND_ADD"},
    # === 2026-08-30 週報新增升評 ===
    "2330": {"exchange": "tse", "name": "台積電", "market": "上市", "theme": "存股核心/AI 晶圓代工", "added_at": "2026-08-30", "note": "2026-08-30 週報升評 76→80；觸 Buy Zone 上緣 2,400；7 月 +44.69% 連 3 月歷史新高；全年美元營收上修至略高於 40%；資本支出上修至 600-640 億美元；存股核心邏輯；等回檔 2,200-2,300 才分批定投"},
    # === 生技/醫材 ===
    "6472": {"exchange": "tse", "name": "保瑞",     "market": "上市", "theme": "CDMO/學名藥", "added_at": "2026-07-16", "note": "2024 收購 Upsher-Smith", "status": "ACCEPTED"},
    "6446": {"exchange": "tse", "name": "藥華藥",   "market": "上市", "theme": "新藥 (P1101)", "added_at": "2026-07-16", "note": "罕病藥、減肥藥海外授權"},
    "4147": {"exchange": "tse", "name": "中裕",     "market": "上市", "theme": "愛滋新藥", "added_at": "2026-07-16", "note": "Trogarzo 已上市"},
    "4123": {"exchange": "tse", "name": "晟德",     "market": "上市", "theme": "生技控股", "added_at": "2026-07-16", "note": "轉投資多家高潛力公司"},
    # === 老大 2026-08-10 新建議加入觀察池 ===
    "7780": {"exchange": "otc", "name": "大研生醫*",   "market": "上櫃", "theme": "保健食品 (魚油)", "added_at": "2026-08-10", "note": "台灣魚油市占第一, 日本順利擴張, 拆股後低價, 庫藏區保護 12.75"},
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
    "6409": "ARCHIVED_TRANSFERRED",  # → 主清單（2026-07-16 接受；修正舊錯碼 4540）
    "6515": "ARCHIVED_TRANSFERRED",  # → 主清單
    # === 達標轉主清單 (老大 2026-08-10 接受) ===
    "5904": "ARCHIVED_TRANSFERRED",  # → 主清單（拆股後基本面 +34.7%）
    # === 達標待 8/1 月度提案 (2026-07-19 週報評估) ===
    "6446": "RECOMMEND_ADD",     # 藥華藥 - 2026-08-09 評分 84，第一新增順位；8/12 法說後 1,020-1,050 分批
    # === 老大 2026-08-10 新觀察池 (待評估) ===
    "7780": "RECOMMEND_ADD",      # 大研生醫* - 2026-08-10 深度評估，月營收連 5 月年增 30%，庫藏區下限 12.75 保護；總評 ⭐⭐⭐⭐ (3.5/5)
    "3131": "WATCH",             # 弘塑 - 2026-07-26 估值/券商目標下修，降為觀察
    "3583": "WATCH",             # 辛耘 - 2026/06 營收年減，等待 Q2 毛利驗證
    "6187": "WATCH",             # 萬潤 - 題材強但千元價位估值風險高
    "2891": "WATCH",             # 中信金 - 獲利穩健但估值已先行反映
    # === 2026-08-09 週報新增 ===
    # === 2026-08-09 週報新增 → 2026-08-10 老大翻盤保留 2,000 股 ===
    "2241": "ARCHIVED_RETAINED",  # 艾姆勒 — 2026-08-10 老大決議保留 2,000 股 @ 34.75 (覆蓋 8/9 移除決議); 觀察 36-38 / 停損 30
    # === 持續 WATCH ===
    "4123": "WATCH",       # 晟德
    # === 繼續 EVALUATING ===
    "4147": "EVALUATING",  # 中裕
    "5309": "NEW",         # 系統電
    "6224": "NEW",         # 聚鼎
    "2884": "EVALUATING",  # 玉山金
    "2885": "RECOMMEND_ADD", # 元大金 - 2026-08-02 評分 78，第二新增順位
    "2882": "EVALUATING",  # 國泰金
    "2603": "EVALUATING",  # 長榮
    "2609": "EVALUATING",  # 陽明
    "1301": "ARCHIVED",    # 台塑 - 2026-08-02 評分 49，產能過剩未根治
    "1303": "EVALUATING",  # 南亞
    "0050": "RECOMMEND_ADD", # ETF 大盤 - 2026-08-02 評分 76，核心定投候選
    "0056": "NEW",         # ETF 高股息
    "00878": "NEW",        # ETF 高股息
    "6224": "ARCHIVED",    # 聚鼎 - 2026-08-02 評分 49，財報/技術未修復
    "3008": "RECOMMEND_ADD",  # 大立光 - 2026-08-30 週報連續 3 週提案；7 月營收 54.13 億月增+31% 寫今年新高 + 法說會看好 8 月拉貨 + Q1 EPS 46.63 + CPO 9 月啟動
    # === 2026-08-30 週報新增升評 ===
    "2330": "RECOMMEND_ADD",  # 台積電 - 2026-08-30 週報升評 76→80；觸 Buy Zone 上緣 2,400；7 月 +44.69% 連 3 月歷史新高；存股核心邏輯；等回檔 2,200-2,300
    "4977": "RECOMMEND_ADD",  # 眾達-KY - 2026-08-30 週報升評 64→70；8/26 漲停 +10%；本週 +14.29%；CPO + 品固雙引擎確認
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
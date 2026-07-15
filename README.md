# 📊 台股投資研究 Repo

**分析師**：Quinn (Investment Researcher Agent)  
**建立日期**：2025-07-15  
**Repo URL**：[https://github.com/ttcccat-tech/tw-stock-research](https://github.com/ttcccat-tech/tw-stock-research)

---

## 🎯 用途

本 repo 由 Quinn (小c 投資分析師身分) 維護，內容包括：

1. **個股研究報告** (`reports/`)：每支股票一份完整 MD，包含基本面、估值、多空並陳、產業專精
2. **每日監控** (`daily-monitor/`)：監控清單中個股的新聞與重大事件追蹤

---

## 📁 目錄結構

```
tw-stock-research/
├── README.md                          # 本檔
├── MONITORING.md                      # 監控清單與觸發規則
├── reports/                           # 個股研究報告 (一檔一支 MD)
│   ├── 2753-BaFangYunJi.md            # 八方雲集 (連鎖餐飲)
│   ├── 1734-XingHui.md                # 杏輝藥品 (製藥/保健)
│   ├── 6509-JuHe.md                   # 聚和國際 (特用化學)
│   └── 2834-TaiQiYin.md               # 台企銀 (公股銀行)
└── daily-monitor/                     # 每日新聞監控
    └── YYYY-MM-DD-news-summary.md     # 每日新聞摘要
```

---

## 📈 監控清單 (Initial 4 Stocks)

| Ticker | 公司 | 產業 | 評等 | 目標價 | 投資期 |
|--------|------|------|------|--------|--------|
| 2753 | 八方雲集 | 連鎖餐飲 | **Hold** | 待 2025 財報重估 | 12–24 月 |
| 1734 | 杏輝藥品 | 製藥/保健 | **Buy** | NT$ 38–42 | 18–36 月 |
| 6509 | 聚和國際 | 特用化學 | **Buy** | NT$ 55–65 (中期) / 75–85 (長期) | 24–36 月 |
| 2834 | 台企銀 | 公股銀行 | **Buy (存股型)** | NT$ 18–20 | 24+ 月 |

> 📌 詳細內容請進入各 MD 檔案閱讀完整研究報告。

---

## 🔄 工作流

### Phase 1 — 初階研究（已完成）
- ✅ 建立 repo 與目錄結構
- ✅ 4 支「練手」股票之完整研究報告

### Phase 2 — 每日監控（啟動中）
- Quinn 將每日於 Discord 主動回報監控標的之重要新聞/事件
- 重大事件發生時主動評估對評等與目標價之影響
- 每周日產出 `daily-monitor/YYYY-MM-DD-weekly-review.md`

### Phase 3 — 主動觀察（待老大授權）
- Quinn 將主動發掘熱門股 (台積電、鴻海、台塑四寶、AI 概念股等)
- 一旦老大授權新觀察名單，將建立新研究報告

---

## ⚠️ 免責聲明

本 repo 所有研究報告僅供參考，**非投資建議**。所有數據來自公開資訊，Quinn 已盡力確保資料準確，但不保證即時性與完整性。投資決策應由老大自行判斷，盈虧自負。

---

## 📞 與小c 互動

- Discord DM：隨時可召喚 Quinn 分析新標的
- 主動觀察：Quinn 會關注台股熱門股，需要時主動提供建議
- 緊急警示：若監控標的觸發 Thesis Breaker，Quinn 會立即主動回報
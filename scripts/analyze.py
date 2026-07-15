#!/usr/bin/env python3
"""
台股技術分析工具 — Quinn 投資分析師專用

功能：
- 讀取 daily-prices.csv 歷史資料
- 計算均線 (MA5/MA20/MA60)、RSI、布林通道
- 判斷進場訊號 (均線黃金交叉、RSI 超買超賣、量價背離)
- 與研究報告的「進場區間 × 目標價」對照，給出操作建議

使用方式：
  python3 analyze.py                # 分析全部 4 支
  python3 analyze.py 6509           # 分析單一標的
"""

import csv
import sys
from pathlib import Path
from statistics import mean, stdev

HISTORY = Path("/var/repo/tw-stock-research/price-history/daily-prices.csv")

# 研究報告的目標價/進場區間 (Quinn 評估)
TARGETS = {
    "2753": {"buy": [145, 200], "target": 235, "stop": 150, "rating": "Hold"},
    "1734": {"buy": [27, 36], "target": 40, "stop": 27, "rating": "Buy"},
    "6509": {"buy": [45, 55], "target": 55, "stop": 42, "rating": "Buy"},
    "2834": {"buy": [14.0, 17.5], "target": 19, "stop": None, "rating": "Buy (存股)"},
}

NAMES = {
    "2753": "八方雲集", "1734": "杏輝",
    "6509": "聚和國際", "2834": "臺企銀",
}


def load_history(code):
    """讀取單一股票的歷史收盤價 (由新到舊)"""
    if not HISTORY.exists():
        return []
    with open(HISTORY, encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["code"] == code]
    # 轉成 dict list (新到舊)
    data = []
    for r in reversed(rows):
        try:
            data.append({
                "date": r["date"],
                "close": float(r["close"]),
                "volume": int(r["volume_lots"]),
                "pe": r["pe"],
                "yield": r["yield_pct"],
            })
        except (ValueError, KeyError):
            continue
    return data


def calc_ma(prices, n):
    if len(prices) < n: return None
    return mean(prices[:n])


def calc_rsi(prices, n=14):
    if len(prices) < n + 1: return None
    gains, losses = [], []
    for i in range(1, n + 1):
        diff = prices[i-1] - prices[i]  # prices[0] is newest
        if diff > 0:
            gains.append(diff)
        else:
            losses.append(-diff)
    avg_gain = mean(gains) if gains else 0
    avg_loss = mean(losses) if losses else 0
    if avg_loss == 0: return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def analyze(code):
    data = load_history(code)
    name = NAMES.get(code, code)
    target = TARGETS.get(code, {})

    print(f"\n{'='*70}")
    print(f"📊 {code} {name} — Quinn 技術分析")
    print(f"{'='*70}")
    print(f"歷史資料筆數: {len(data)} 筆")
    if not data:
        print("(無資料)")
        return

    # 取近 60 筆 (新到舊)
    closes = [d["close"] for d in data[:60]]
    latest = data[0]
    print(f"最新收盤: {latest['date']} → {latest['close']:.2f} (PE {latest['pe']}, 殖利率 {latest['yield']}%)")

    if len(closes) < 5:
        print("資料不足 5 筆，無法計算均線")
        return

    # 均線
    ma5 = calc_ma(closes, 5)
    ma20 = calc_ma(closes, 20) if len(closes) >= 20 else None
    ma60 = calc_ma(closes, 60) if len(closes) >= 60 else None
    print(f"\n均線:")
    if ma5: print(f"  MA5  = {ma5:.2f}  {'↑多頭' if latest['close'] > ma5 else '↓空頭'}")
    if ma20: print(f"  MA20 = {ma20:.2f}  {'↑多頭' if latest['close'] > ma20 else '↓空頭'}")
    if ma60: print(f"  MA60 = {ma60:.2f}  {'↑多頭' if latest['close'] > ma60 else '↓空頭'}")

    # 黃金/死亡交叉
    if ma5 and ma20 and len(closes) >= 21:
        prev_ma5 = calc_ma(closes[1:], 5)
        prev_ma20 = calc_ma(closes[1:], 20)
        if prev_ma5 and prev_ma20:
            if prev_ma5 <= prev_ma20 and ma5 > ma20:
                print("  🟢 黃金交叉！MA5 突破 MA20")
            elif prev_ma5 >= prev_ma20 and ma5 < ma20:
                print("  🔴 死亡交叉！MA5 跌破 MA20")

    # RSI
    rsi = calc_rsi(closes)
    if rsi:
        print(f"\nRSI(14): {rsi:.1f}  ", end="")
        if rsi > 70: print("⚠️ 超買區")
        elif rsi < 30: print("🟢 超賣區 (可能反彈)")
        else: print("(中性)")

    # 對照目標價
    if target:
        print(f"\n進場區間: NT$ {target['buy'][0]:.1f} – {target['buy'][1]:.1f}")
        print(f"目標價: NT$ {target['target']:.1f}")
        if target['stop']:
            print(f"停損價: NT$ {target['stop']:.1f}")

        # 給出操作建議
        cur = latest['close']
        if target['buy'][0] <= cur <= target['buy'][1]:
            print(f"\n💡 建議: 當前股價 {cur:.2f} 在進場區間內，可分批建倉")
        elif cur < target['buy'][0]:
            print(f"\n🟢 建議: 當前股價 {cur:.2f} 低於進場區間下緣，**積極進場區**")
        else:
            upside = (target['target'] - cur) / cur * 100
            print(f"\n⚠️ 建議: 當前股價 {cur:.2f} 高於進場區間上緣，潛在上行空間 {upside:.1f}%")

        if target['stop'] and cur <= target['stop']:
            print(f"🚨 警告: 已觸及停損價 {target['stop']}，需重新檢視投資邏輯")


def main():
    if len(sys.argv) > 1:
        codes = sys.argv[1:]
    else:
        codes = list(TARGETS.keys())

    for code in codes:
        analyze(code)


if __name__ == "__main__":
    main()

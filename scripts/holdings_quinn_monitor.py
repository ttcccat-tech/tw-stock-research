#!/usr/bin/env python3
"""
所有持股 — 中期持有 Quinn 深度分析監控 (升級版)

老大 SOP (2026-07-28 升級):
- 不只是看月營收數字
- 還要有 Quinn 投資分析師的專業觀點
- 包含: 基本面評估、技術面、籌碼面、風險評估

Quinn 分析面向:
1. 個股動能 (月營收/季EPS/客戶訂單)
2. 產業趨勢位置 (順風/逆風/轉折點)
3. 技術面位置 (支撐/壓力/趨勢)
4. 籌碼面 (法人/主力流向)
5. 風險評估 (波動/客戶集中/匯率)
6. 投資建議 (持有/加碼/減碼/出場)
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


# ========== 各股 Quinn 投資分析師專業觀點 ==========
# 這個檔案是 Quinn 的核心分析模組，包含每支持股的深度評估
QUINN_ANALYSIS = {
    "2753": {  # 八方雲集
        "name": "八方雲集",
        "thesis": "存股型餐飲龍頭，靠展店 + 同店成長雙引擎",
        "key_questions": [
            "Q1: 同店營收是否年增 (目標 +5%)?",
            "Q2: 新展店家數是否達標 (年 80-100 家)?",
            "Q3: 原物料 (豬肉/蔬菜) 成本是否穩定?",
            "Q4: 國外市場 (香港/中國) 恢復動能?",
        ],
        "industry_view": "餐飲復甦穩健, 但人口外流 + 外送平台競爭是長期挑戰",
        "bull_case": "新展店超預期 + 同店營收轉正 → 加碼訊號",
        "bear_case": "同店連 2 月年減 + 原物料飆漲 → 警戒訊號",
        "time_horizon": "中期 12-18 月持有, 享受復甦 + 配息",
        "stop_loss": "150.00",
        "add_signal": "跌至 165-170 區間 (Buy Zone 下緣)",
        "reduce_signal": "突破 220 (目標價), 部分獲利了結",
        "key_risks": ["人口外流", "外送平台競爭", "原物料波動"],
    },
    "6509": {  # 聚和國際
        "name": "聚和國際",
        "thesis": "全球生物緩衝劑前 2 大, 2028 屏科廠 2 倍產能",
        "key_questions": [
            "Q1: 月營收年增是否持續 > 5%?",
            "Q2: 屏科廠工程進度 (目標 2027 底完工)?",
            "Q3: 高端生物緩衝劑市占率是否提升?",
            "Q4: 大陸削價競爭是否影響毛利?",
        ],
        "industry_view": "生技製藥需求長期成長, Marketresearch.biz 預估 2032 年市場 18.59 億美元 (CAGR +9.4%)",
        "bull_case": "屏科廠如期量產 + 高端市占提升至 25% → 目標 NT$ 70-80",
        "bear_case": "屏科廠延遲 + 大陸殺價戰 → 下修至 NT$ 40-45",
        "time_horizon": "長期 18-24 月持有, 等待 2028 屏科廠量產爆發",
        "stop_loss": "40.00",
        "add_signal": "跌至 45-46 (Buy Zone 下緣) 加碼第三批",
        "reduce_signal": "突破 65 (12 月目標) 開始評估部分獲利",
        "key_risks": ["屏科廠延遲", "大陸削價", "匯率波動"],
    },
    "2241": {  # 艾姆勒
        "name": "艾姆勒",
        "thesis": "車用逆變器散熱模組龍頭, 800V + AI 雙引擎",
        "key_questions": [
            "Q1: 月營收年增是否維持 > 30%?",
            "Q2: Continental/Infineon 訂單是否穩定?",
            "Q3: 800V 平台滲透率提升進度?",
            "Q4: AI 浸沒式散熱實際接單狀況?",
        ],
        "industry_view": "EV 800V 平台 2028 達 40%+, AI 散熱新題材, 雙引擎成長",
        "bull_case": "800V + AI 同步發酵 → 目標 NT$ 75-85",
        "bear_case": "客戶砍單 + 全球車市反轉 → 跌破 NT$ 30 停損",
        "time_horizon": "中期 12-18 月持有, 等待雙引擎兌現",
        "stop_loss": "30.00",
        "add_signal": "反彈訊號觸發 (站上 35-36) 考慮加碼",
        "reduce_signal": "突破 60 (12 月目標) 部分獲利",
        "key_risks": ["客戶集中度 90%", "全球車市", "AI 題材落空"],
    },
    "2834": {  # 臺企銀
        "name": "臺企銀",
        "thesis": "公股銀行存股標的, 5.5% 殖利率 + 0.7 股票股利",
        "key_questions": [
            "Q1: 月營收/淨利是否穩定年增?",
            "Q2: 資本適足率是否 > 13%?",
            "Q3: 逾放比是否維持 < 0.2%?",
            "Q4: 央行利率政策變化?",
        ],
        "industry_view": "升息循環已結束, 但存放利差穩定, 中小企業放款龍頭地位穩固",
        "bull_case": "H2 淨利持續年增 + 央行不降息 → 目標 NT$ 20-22",
        "bear_case": "央行降息 2 碼 + 中小企違約率上升 → NT$ 16-17",
        "time_horizon": "長期 24 月以上持有, 享受每年配息 + 股票股利放大",
        "stop_loss": "16.00",
        "add_signal": "跌至 17.0 以下加碼, 跌破 16.0 大膽加碼",
        "reduce_signal": "突破 21.0 開始評估部分獲利",
        "key_risks": ["央行降息", "公股政策", "中小企業違約"],
    },
}


def get_holdings():
    """從 DB 取得所有持股"""
    if not DB_PATH.exists():
        return []
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute("""
        SELECT ticker, name, shares, avg_cost
        FROM holdings
        WHERE shares > 0
        ORDER BY ticker
    """)
    rows = cur.fetchall()
    conn.close()
    return rows


def get_recent_prices(code, n=20):
    """從 DB 取最近 n 筆歷史價格"""
    if not DB_PATH.exists():
        return []
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute("""
        SELECT date, close FROM price_history
        WHERE ticker=? AND close IS NOT NULL
        ORDER BY date DESC LIMIT ?
    """, (code, n))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_rating(code):
    """從 watchlist 取評等與 Buy Zone"""
    sys.path.insert(0, str(REPO_DIR / "scripts"))
    from watchlist import BUY_ZONES
    return BUY_ZONES.get(code, {})


def calc_technical(prices):
    """計算技術指標"""
    if len(prices) < 5:
        return None
    closes = [p[1] for p in prices]
    ma5 = sum(closes[:5]) / 5 if len(closes) >= 5 else None
    ma10 = sum(closes[:10]) / 10 if len(closes) >= 10 else None
    current = closes[0]
    trend = "上升" if current > ma5 else "下降"
    momentum = ((current - closes[4]) / closes[4] * 100) if len(closes) >= 5 else 0
    return {
        "current": current,
        "ma5": ma5,
        "ma10": ma10,
        "trend_5d": trend,
        "momentum_5d": momentum,
    }


def calc_pnl(current, cost, shares):
    """計算損益"""
    pnl = (current - cost) * shares
    pct = ((current - cost) / cost * 100) if cost > 0 else 0
    return pnl, pct


def quinn_analyst_view(ticker, name, current_price, cost, shares, tech, zone):
    """Quinn 投資分析師觀點"""
    analysis = QUINN_ANALYSIS.get(ticker, {})
    pnl, pnl_pct = calc_pnl(current_price, cost, shares)

    # 動能評估
    momentum = tech["momentum_5d"] if tech else 0
    if momentum > 5:
        momentum_label = "🚀 強勢上漲"
        momentum_score = 2
    elif momentum > 0:
        momentum_label = "📈 溫和上漲"
        momentum_score = 1
    elif momentum > -5:
        momentum_label = "📉 溫和下跌"
        momentum_score = -1
    else:
        momentum_label = "⚠️ 明顯下跌"
        momentum_score = -2

    # 趨勢評估
    trend_5d = tech["trend_5d"] if tech else "N/A"

    # 損益狀態
    if pnl_pct > 10:
        pnl_label = "🟢 獲利 > 10%"
        pnl_score = 2
    elif pnl_pct > 0:
        pnl_label = "🟡 獲利中"
        pnl_score = 1
    elif pnl_pct > -10:
        pnl_label = "🟡 小虧中"
        pnl_score = 0
    else:
        pnl_label = "🔴 虧損 > 10%"
        pnl_score = -1

    # Buy Zone 位置
    buy_min = zone.get("buy_min", 0)
    buy_max = zone.get("buy_max", 0)
    target = zone.get("target", 0)
    stop = zone.get("stop", 0)

    if buy_min and buy_max:
        if current_price <= buy_min:
            position_label = "💎 買進區下緣 (加碼好時機)"
        elif current_price <= buy_max:
            position_label = "🟢 買進區內 (合理持有)"
        else:
            position_label = "⚪ 買進區上方 (觀察)"
    else:
        position_label = "🟡 無 Buy Zone"

    # 距離目標價
    if target:
        upside = ((target - current_price) / current_price * 100)
        if upside > 30:
            upside_label = f"🚀 距目標 +{upside:.1f}% (空間大)"
        elif upside > 0:
            upside_label = f"📈 距目標 +{upside:.1f}%"
        else:
            upside_label = f"⚠️ 已達目標 (獲利了結)"
    else:
        upside_label = "N/A"
        upside = 0

    # Quinn 整體評估
    total_score = momentum_score + pnl_score
    if total_score >= 3:
        overall = "🟢 Quinn: 強烈看好 (加碼時機)"
    elif total_score >= 1:
        overall = "🟢 Quinn: 看好 (持有)"
    elif total_score >= -1:
        overall = "🟡 Quinn: 中性 (觀察)"
    elif total_score >= -3:
        overall = "🟠 Quinn: 保守 (減碼)"
    else:
        overall = "🔴 Quinn: 悲觀 (出場)"

    return {
        "momentum_label": momentum_label,
        "momentum_score": momentum_score,
        "trend_5d": trend_5d,
        "pnl_label": pnl_label,
        "pnl_score": pnl_score,
        "pnl": pnl,
        "pnl_pct": pnl_pct,
        "position_label": position_label,
        "upside_label": upside_label,
        "upside_pct": upside,
        "overall": overall,
        "analysis_data": analysis,
    }


def send_discord(message):
    """推播 Discord"""
    try:
        from hermes_tools import send_message as sm
        sm(action="send", message=message)
        return True
    except Exception:
        return False


def main():
    print(f"\n📊 Quinn 中期持有深度分析監控 (升級版)")
    print(f"   不只財報，更包含投資分析師觀點")
    print()

    holdings = get_holdings()
    if not holdings:
        print("⚠️ 無庫存資料")
        return 0

    today = datetime.now()
    is_month_start = today.day <= 5

    summary_lines = []

    for ticker, name, shares, cost in holdings:
        prices = get_recent_prices(ticker, n=20)
        if not prices:
            summary_lines.append(f"⚠️ {ticker} {name}: 無價格資料")
            continue

        tech = calc_technical(prices)
        zone = get_rating(ticker)
        view = quinn_analyst_view(ticker, name, tech["current"], cost, shares, tech, zone)
        analysis = view["analysis_data"]

        # 組合單一個股分析
        stock_analysis = (
            f"\n{'='*70}\n"
            f"📊 **{ticker} {name}** ({analysis.get('thesis', '')})\n"
            f"{'='*70}\n\n"
            f"**【股價狀態】**\n"
            f"  現價: {tech['current']}\n"
            f"  持股: {shares:,} 股 @ {cost}\n"
            f"  損益: {view['pnl']:+,.0f} ({view['pnl_pct']:+.2f}%)\n"
            f"  5日動能: {view['momentum_label']} ({tech['momentum_5d']:+.2f}%)\n"
            f"  5MA: {tech['ma5']:.2f} ({view['trend_5d']})\n"
            f"  距目標: {view['upside_label']}\n\n"
            f"**【Quinn 投資邏輯】**\n"
            f"  投資論點: {analysis.get('thesis', 'N/A')}\n"
            f"  產業觀點: {analysis.get('industry_view', 'N/A')}\n"
            f"  持有期間: {analysis.get('time_horizon', 'N/A')}\n\n"
            f"**【追蹤重點問題】** (月初檢查)\n"
        )
        for i, q in enumerate(analysis.get('key_questions', []), 1):
            stock_analysis += f"  {q}\n"

        stock_analysis += (
            f"\n**【Quinn 風險評估】**\n"
            f"  主要風險: {' / '.join(analysis.get('key_risks', []))}\n"
            f"  停損價: {analysis.get('stop_loss', 'N/A')}\n\n"
            f"**【Quinn 進退場建議】**\n"
            f"  🟢 加碼訊號: {analysis.get('add_signal', 'N/A')}\n"
            f"  🔴 減碼訊號: {analysis.get('reduce_signal', 'N/A')}\n\n"
            f"**【情境分析】**\n"
            f"  樂觀: {analysis.get('bull_case', 'N/A')}\n"
            f"  悲觀: {analysis.get('bear_case', 'N/A')}\n\n"
            f"**【Quinn 整體評估】**: {view['overall']}\n"
        )
        summary_lines.append(stock_analysis)

    # 月初推播
    if is_month_start:
        msg = (
            f"📊 **所有持股 — Quinn 中期深度分析** ({today.strftime('%Y/%m/%d')})\n\n"
            f"老大您的 {len(holdings)} 支持股 — Quinn 投資分析師觀點：\n\n" +
            "\n".join(summary_lines) +
            f"\n\n💡 **Quinn 月初 SOP 提醒**:\n"
            f"  1. 查看每支持股的「追蹤重點問題」並回答\n"
            f"  2. 檢查「進退場建議」是否符合老大計畫\n"
            f"  3. 評估「Quinn 整體評估」是否需要調整\n"
            f"  4. 如果有疑慮，主動回報給 Quinn 重新評估\n\n"
            f"⏰ 下次提醒: 下個月 1-5 號 09:00"
        )
        if send_discord(msg):
            print("✅ Discord 深度分析已送出")
        else:
            print("⚠️ Discord 推播失敗")

    print("\n📋 持股組合分析:")
    for line in summary_lines:
        print(line)
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
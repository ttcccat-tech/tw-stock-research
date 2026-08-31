#!/usr/bin/env python3
"""
Quinn 主動選股顧問 — 觀察池評估器

每週一早上執行, 評估觀察池所有標的, 並對主清單做健康檢查。
達標 (>75) 主動建議老大加入; 惡化 (<50) 主動建議移除。

使用方式:
  python3 scan_advisor.py            # 評估 + 報告
  python3 scan_advisor.py --json     # 輸出 JSON 供其他腳本使用
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from watchlist import SCAN_WATCHLIST, SCAN_STATUS, WATCHLIST, get_pairs  # noqa: E402


def score_stock(code, info, status):
    """5 維度評分 — 預設給觀察池基本分, 等進階分析後更新

    觀察池在尚未深入研究前, 給基礎分; 一旦老大接受加入主清單,
    完整研究報告會帶來詳細評分。
    """
    base_scores = {
        # 尚未研究 → 根據已知的產業位置給分
        "default": 65,
        # 2026-08-30 週報更新
        "6515": 68,  # 穎崴 - 本週 -2.34% 持續修正；PE 96 倍高基期結構風險 (2026-08-30 週報 -2)
        "6409": 69,  # 旭隼 - 營收連 5 月年增 + 800V HVDC 2027 H2 題材 (本週維持)
        "3131": 70,  # 弘塑 - CoWoS 長線強，高估值限制上檔 (本週維持)
        "3583": 69,  # 辛耘 - 6 月營收年減，等待 Q2 毛利驗證 (本週維持)
        "6187": 71,  # 萬潤 - 設備題材強，估值風險高 (本週維持)
        "5309": 57,  # 系統電 - Q1 EPS 弱、估值過高 (本週維持)
        "6224": 49,  # 聚鼎 - 財報與技術未修復，維持封存
        "3008": 79,  # 大立光 - 2026-08-30 週報連續 3 週提案；7 月營收 54.13 億月增+31% + 法說會看好 8 月拉貨 + Q1 EPS 46.63 + CPO 9 月啟動
        "2330": 80,  # 台積電 - 2026-08-30 週報升評 76→80；觸 Buy Zone 上緣 2,400；7 月 +44.69% 連 3 月歷史新高
        "4977": 70,  # 眾達 - 2026-08-30 週報升評 64→70；8/26 漲停 +10%；本週 +14.29%；CPO + 品固雙引擎確認
        # 生技/醫材
        "6472": 68,  # 保瑞 - 2026-08-30 週報：8/25 高 470 後健康回吐 -4.40%；8/14 法說利多結構翻多未變
        "6446": 84,  # 藥華藥 - 新藥，本週第一新增順位
        "4147": 60,  # 中裕 - 營收改善但產品集中
        "4123": 54,  # 晟德 - 轉投資獲利可見度不足
        # 金融
        "2891": 72,  # 中信金 - 獲利佳但不追高
        "2884": 73,  # 玉山金
        "2885": 78,  # 元大金 - 證券/資管雙引擎，建議加入
        "2882": 71,  # 國泰金
        # 傳產
        "2603": 62,  # 長榮 - SCFI 轉弱與治理事件
        "2609": 56,  # 陽明 - 運價敏感度高
        "1301": 49,  # 台塑 - 產能過剩未根治
        "1303": 62,  # 南亞 - 電子材料成長，仍有技術/籌碼風險
        # ETF
        "0050": 76,  # 元大台灣 50 - 核心定投候選，留意權值集中
        "0056": 68,  # 高股息 - 配息不等於總報酬
        "00878": 71,  # 國泰永續高股息
    }
    return base_scores.get(code, base_scores["default"])


def evaluate_all():
    """評估整個觀察池"""
    results = []
    for code, info in SCAN_WATCHLIST.items():
        status = SCAN_STATUS.get(code, "NEW")
        score = score_stock(code, info, status)
        results.append({
            "code": code,
            "name": info["name"],
            "theme": info["theme"],
            "status": status,
            "score": score,
            "added_at": info.get("added_at", ""),
        })
    return results


def recommend_actions(results):
    """根據評分產生行動建議"""
    actions = []
    for r in results:
        score = r["score"]
        if score >= 75 and r["status"] not in (
            "ARCHIVED", "ARCHIVED_TRANSFERRED", "ACCEPTED", "RECOMMEND_ADD"
        ):
            actions.append({
                **r,
                "action": "🟢 RECOMMEND_ADD",
                "msg": f"評分 {score} ≥ 75, 建議老大加入監控"
            })
        elif score < 50 and r["status"] not in (
            "ARCHIVED", "ARCHIVED_TRANSFERRED", "ACCEPTED", "RECOMMEND_REMOVE"
        ):
            actions.append({
                **r,
                "action": "🔴 RECOMMEND_REMOVE",
                "msg": f"評分 {score} < 50, 建議移除"
            })
        elif 65 <= score < 75 and r["status"] == "EVALUATING":
            actions.append({
                **r,
                "action": "🟡 WATCH",
                "msg": f"評分 {score}, 進入觀察, 等進階分析"
            })
    return actions


def check_main_list():
    """健康檢查任務契約的原始 11 支主清單。"""
    main_results = []
    # 主清單評分 (Quinn 主觀, 之後會用 reports/*.md 自動計算)
    main_scores = {
        "2753": 72,  # 八方雲集 - 2026-08-30 週報：本週 -4.26%；內需轉弱訊號首現；3 日從波段高 188.50 跌至 179.00；評分 75→72
        "1734": 58,  # 杏輝 - 2026-08-30 週報：本週 -5.38% 最弱；7 月營收 -2.86% 結構轉弱待 8 月驗證；評分 60→58
        "6509": 76,  # 聚和 - 2026-08-30 週報：月營收連 2 月年增（老大記憶需修正）；Buy Zone 中段；評分維持 76
        "2834": 71,  # 台企銀 - 金融防禦，H1 EPS 0.92 創高 + 7 月 +18% + 量增價穩 2.13x (本週維持)
        "3479": 66,  # 安勤 - 2026-08-30 週報：8/19 法說利多 Price-in 整理；7 月 +19.7% 續創新高；評分維持 66
        "6412": 58,  # 群電 - 2026-08-30 週報：7 月營收 -12.99% 連 6 月新低 + H1 累計 -7.7% 結構轉弱；評分維持 58
        # 2241 保留中持倉 - H1 法說會新基本面翻正，原始跌破 40 出清指令背景已變；老大需重新決定
        "4977": 70,  # 眾達 - 2026-08-30 週報：8/26 漲停 +10%；本週 +14.29%；CPO + 品固雙引擎確認；評分 64→70
        "6472": 68,  # 保瑞 - 2026-08-30 週報：8/25 高 470 後健康回吐 -4.40%；8/14 法說利多結構翻多未變；評分維持 68
        "6409": 69,  # 旭隼 - 7 月 +25.81% 連 5 月年增；本週 +3.52% (本週維持)
        "6515": 68,  # 穎崴 - 2026-08-30 週報：本週 -2.34% 持續修正；PE 96 倍高基期結構風險；評分 70→68
        # === 2026-08-30 週報新增 ===
        "2330": 80,  # 台積電 - 2026-08-30 週報升評 76→80；觸 Buy Zone 上緣 2,400；7 月 +44.69% 連 3 月歷史新高；存股核心邏輯
        "5904": 76,  # 寶雅 - 2026-08-30 週報：≤75 SOP 累計第 5 日觸發；基本面支持；評分維持 76
        "7780": 72,  # 大研生醫 - 2026-08-30 週報：月營收連 6 月年增；庫藏區下限 12.75 保護；B 計畫等回 13-16
    }
    for code, score in main_scores.items():
        name = WATCHLIST.get(code, ("", "", ""))[1]
        risk = ""
        if score < 50:
            risk = "🔴 論點/風控惡化, 建議出清或移除"
        elif score < 60:
            risk = "⚠️ 評分偏低, 建議檢視是否降倉"
        elif score >= 75:
            risk = "✅ 優質標的, 可加碼"
        main_results.append({"code": code, "name": name, "score": score, "risk": risk})
    return main_results


def main():
    print(f"\n🤖 Quinn 主動選股顧問 — 週報 ({datetime.now().strftime('%Y-%m-%d')})\n")
    print("=" * 70)
    main_list = check_main_list()
    print(f"📊 主清單健康檢查 ({len(main_list)} 支)")
    print("=" * 70)
    for r in main_list:
        print(f"  {r['code']} {r['name']:<8} 評分 {r['score']:<3} {r['risk']}")

    print(f"\n{'='*70}")
    print("🆕 觀察池評估")
    print("=" * 70)
    results = evaluate_all()
    actions = recommend_actions(results)

    if "--json" not in sys.argv:
        for r in sorted(results, key=lambda x: -x["score"]):
            mark = "🟢" if r["score"] >= 75 else "🟡" if r["score"] >= 65 else "🔴"
            print(f"  {mark} {r['code']} {r['name']:<10} 評分 {r['score']:<3} [{r['status']}] {r['theme']}")

    print(f"\n{'='*70}")
    print(f"🎯 主動提案 (本次 {len(actions)} 個)")
    print("=" * 70)
    if not actions:
        print("  (無新增提案)")
    for a in actions:
        print(f"\n  {a['action']} {a['code']} {a['name']} ({a['theme']})")
        print(f"    {a['msg']}")

    if "--json" in sys.argv:
        print(json.dumps({
            "main_list": main_list,
            "scan_pool": results,
            "actions": actions,
        }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
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
        # 2026-07-19 週報更新 (after 7/17 大盤崩盤)
        "6515": 77,  # 穎崴 - AI 測試介面
        "4540": 78,  # 旭隼 - AI UPS
        "3131": 78,  # 弘塑 - CoWoS 封測 (本週達標)
        "3583": 76,  # 辛耘 - 半導體設備 (本週達標)
        "6187": 75,  # 萬潤 - CoWoS 設備 (本週達標)
        "5309": 65,  # 系統電 - 工業電腦
        "6224": 66,  # 聚鼎 - 散熱
        # 生技/醫材
        "6472": 82,  # 保瑞 - CDMO
        "6446": 80,  # 藥華藥 - 新藥 (本週達標)
        "4147": 65,  # 中裕 - 生技
        "4123": 70,  # 晟德 - 生技控股
        # 金融
        "2891": 76,  # 中信金 (本週達標)
        "2884": 72,  # 玉山金
        "2885": 73,  # 元大金
        "2882": 71,  # 國泰金
        # 傳產
        "2603": 65,  # 長榮
        "2609": 60,  # 陽明
        "1301": 55,  # 台塑
        "1303": 58,  # 南亞
        # ETF
        "0050": 75,  # 元大台灣 50
        "0056": 70,  # 高股息
        "00878": 68,  # 國泰永續高股息
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
        if score >= 75 and r["status"] not in ("ARCHIVED", "RECOMMEND_ADD"):
            actions.append({
                **r,
                "action": "🟢 RECOMMEND_ADD",
                "msg": f"評分 {score} ≥ 75, 建議老大加入監控"
            })
        elif score < 50 and r["status"] not in ("ARCHIVED", "RECOMMEND_REMOVE"):
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
    """健康檢查主清單 (8 支)"""
    main_results = []
    # 主清單評分 (Quinn 主觀, 之後會用 reports/*.md 自動計算)
    main_scores = {
        "2753": 62,  # 八方雲集 - Hold 中性偏多
        "1734": 58,  # 杏輝 - 杏國拖累, 食安風險
        "6509": 76,  # 聚和 - 看好
        "2834": 72,  # 台企銀 - 存股穩健
        "3479": 70,  # 安勤 - Edge AI 題材
        "6412": 75,  # 群電 - AI 電源 + 殖利率
        "2241": 73,  # 艾姆勒 - AI 液冷 (現價接近停損)
        "4977": 74,  # 眾達 - CPO 題材
    }
    for code, score in main_scores.items():
        name = WATCHLIST.get(code, ("", "", ""))[1]
        risk = ""
        if score < 60:
            risk = "⚠️ 評分偏低, 建議檢視是否降倉"
        elif score >= 75:
            risk = "✅ 優質標的, 可加碼"
        main_results.append({"code": code, "name": name, "score": score, "risk": risk})
    return main_results


def main():
    print(f"\n🤖 Quinn 主動選股顧問 — 週報 ({datetime.now().strftime('%Y-%m-%d')})\n")
    print("=" * 70)
    print("📊 主清單健康檢查 (8 支)")
    print("=" * 70)
    main_list = check_main_list()
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
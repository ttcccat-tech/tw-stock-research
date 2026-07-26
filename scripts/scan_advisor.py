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
        "6409": 72,  # 旭隼 - 修正錯碼；營收轉正但 HVDC 貢獻仍遠
        "3131": 67,  # 弘塑 - 題材強，但估值與券商目標價下修
        "3583": 66,  # 辛耘 - 6 月營收年減，等待 Q2 毛利驗證
        "6187": 68,  # 萬潤 - 設備題材強，千元價位估值風險高
        "5309": 54,  # 系統電 - Q1 EPS 弱、估值過高
        "6224": 48,  # 聚鼎 - 財報與技術惡化，建議封存
        # 生技/醫材
        "6472": 64,  # 保瑞 - 關稅/併購整合風險，暫緩新增
        "6446": 80,  # 藥華藥 - 新藥 (本週達標)
        "4147": 57,  # 中裕 - 營收改善但產品集中
        "4123": 52,  # 晟德 - 轉投資獲利可見度不足
        # 金融
        "2891": 73,  # 中信金 - 獲利佳但不追高
        "2884": 73,  # 玉山金
        "2885": 73,  # 元大金
        "2882": 72,  # 國泰金
        # 傳產
        "2603": 62,  # 長榮 - SCFI 轉弱與治理事件
        "2609": 55,  # 陽明 - 運價敏感度高
        "1301": 48,  # 台塑 - 產能過剩未根治
        "1303": 52,  # 南亞 - 營收成長但技術/籌碼惡化
        # ETF
        "0050": 70,  # 元大台灣 50 - 權值集中
        "0056": 68,  # 高股息 - 配息不等於總報酬
        "00878": 69,  # 國泰永續高股息
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
        "2753": 72,  # 八方雲集 - 營收穩健、持倉續抱
        "1734": 57,  # 杏輝 - 增速降溫，建議降倉
        "6509": 76,  # 聚和 - 看好
        "2834": 69,  # 台企銀 - 接近目標，除權息後再評估
        "3479": 79,  # 安勤 - 營收加速，但不追高
        "6412": 63,  # 群電 - 營收仍連續年減
        "2241": 48,  # 艾姆勒 - 盈餘未驗證、風控反覆被測
        "4977": 70,  # 眾達 - CPO 強勢，H1 營收仍弱
        "6472": 61,  # 保瑞 - 關稅與整合風險，等 Q2
        "6409": 74,  # 旭隼 - 營收轉正、HVDC 遠期選擇權
        "6515": 77,  # 穎崴 - 基本面最強、估值風險高
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
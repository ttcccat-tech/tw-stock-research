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
        "6515": 71,  # 穎崴 - 基本面最強、PE 146.93 倍高基期獲利了結 (2026-08-16 週報 -3)
        "6409": 69,  # 旭隼 - 營收轉正但 H1 仍年減，HVDC 貢獻仍遠 (本週維持)
        "3131": 70,  # 弘塑 - CoWoS 長線強，高估值限制上檔 (本週維持)
        "3583": 69,  # 辛耘 - 6 月營收年減，等待 Q2 毛利驗證 (本週維持)
        "6187": 71,  # 萬潤 - 設備題材強，估值風險高 (本週維持)
        "5309": 57,  # 系統電 - Q1 EPS 弱、估值過高 (本週維持)
        "6224": 49,  # 聚鼎 - 財報與技術未修復，維持封存
        "3008": 79,  # 大立光 - 2026-08-16 週報升級 RECOMMEND_ADD；7 月營收 54.13 億月增+31% + 法說會看好 8 月拉貨 + Q1 EPS 46.63 + CPO 9 月啟動
        # 生技/醫材
        "6472": 65,  # 保瑞 - 關稅/併購整合風險，暫緩新增
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
        "2753": 75,  # 八方雲集 - 營收穩健、防禦抗跌 (本週維持)
        "1734": 60,  # 杏輝 - 7 月營收 -2.86% 結構轉弱待 8 月驗證 (本週維持)
        "6509": 76,  # 聚和 - 2026-08-16 週報：H1 EPS 2.16 + 毛利率 35.66% + 7 月 +12.0% 連 3 月年增修復邏輯完整；主清單評分 75→76
        "2834": 71,  # 台企銀 - 金融防禦，H1 EPS 0.92 創高 + 7 月 +18% + 量增價穩 2.13x (本週維持)
        "3479": 66,  # 安勤 - 2026-08-16 週報：8/14 -7.17% 個股孤立弱勢拖累；主清單評分 68→66
        "6412": 58,  # 群電 - 2026-08-16 週報：7 月營收 -12.99% 連 5 月新低 + 累計 -8.41% 結構轉弱；主清單評分 60→58
        # 2241 已於 2026-08-09 週報決議從主清單移除 (ARCHIVED_REMOVED)；8/14 老大指令跌破 40 全部出清
        "4977": 64,  # 眾達 - 2026-08-16 週報：7 月營收 +136.63% 爆發 + 連 3 日站穩 145 三重確認達成；主清單評分 62→64
        "6472": 65,  # 保瑞 - 7 月營收 +5.77% 近持平 + Rockville CDMO 7 月交割 (本週維持)
        "6409": 69,  # 旭隼 - 7 月 +25.81% 連 4 月年增 (本週維持)
        "6515": 71,  # 穎崴 - 基本面最強、PE 146.93 倍高基期獲利了結；主清單評分 74→71
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
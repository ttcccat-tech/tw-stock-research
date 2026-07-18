#!/usr/bin/env python3
"""
Quinn 每日分析觸發器
排程觸發後:
1. 確保 DB 資料最新 (執行 fetch_prices + db_init)
2. 寫入一個「今日分析待辦」記錄
3. 發送 Discord 提醒給 Quinn 自己 (用特殊 tag 觸發 Quinn 醒來分析)

Quinn 的角色:
- cron 只負責收集資料 + 提醒 Quinn
- 「具體分析」必須由 Quinn (這個 agent) 主動撰寫
"""
import sys
import os
import subprocess
from datetime import datetime, date
from pathlib import Path

REPO_DIR = Path("/var/repo/tw-stock-research")
LOGS_DIR = REPO_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)


def run_script(script_name):
    """執行一個腳本並回傳結果"""
    result = subprocess.run(
        ["python3", str(REPO_DIR / "scripts" / script_name)],
        capture_output=True, text=True, timeout=60,
        cwd=str(REPO_DIR)
    )
    return result.returncode, result.stdout, result.stderr


def notify_quinn_to_analyze(alert_count, summary):
    """發送 Discord 訊息，標記 @Quinn 觸發分析"""
    today = date.today().isoformat()
    title = f"📊 Quinn 每日分析任務 ({today})"
    content = (
        f"**資料狀態**：\n{summary}\n\n"
        f"**Quinn 待辦**：\n"
        f"1. 檢視 11 支最新現價與新聞\n"
        f"2. 識別利多利空 (尤其 2241 艾姆勒停損、6509 聚和連三月年減)\n"
        f"3. 產出每日分析 MD → reports/daily/daily-{today}.md\n"
        f"4. 寫入 DB (INSERT INTO reports)\n"
        f"5. Discord 推播精簡版 (3-5 行)\n\n"
        f"**注意**：老大要的是 Quinn 的專業分析 (不是自動產生)。\n"
        f"請在收到本通知後，依序完成上述 5 步驟。"
    )
    # 用 hermes send
    try:
        subprocess.run(
            ["hermes", "send", "-t", "discord", "-s", title, content],
            check=True, timeout=30
        )
        return True
    except Exception as e:
        print(f"[WARN] Discord 通知失敗: {e}")
        return False


def main():
    now = datetime.now()
    today = date.today().isoformat()
    print(f"[{now.strftime('%H:%M:%S')}] Quinn 每日分析觸發器啟動")

    # Step 1: 抓收盤價
    print("Step 1: 抓收盤價...")
    rc, out, err = run_script("fetch_prices.py")
    if rc != 0:
        print(f"  ❌ fetch_prices 失敗: {err}")
        return 1
    print(f"  ✅ {out.split(chr(10))[-2] if out else 'OK'}")

    # Step 2: 同步到 DB
    print("Step 2: 同步 DB...")
    rc, out, err = run_script("db_init.py")
    if rc != 0:
        print(f"  ❌ db_init 失敗: {err}")
        return 1
    print(f"  ✅ DB 已更新")

    # Step 3: 統計現價缺失
    import sqlite3
    conn = sqlite3.connect(str(REPO_DIR / "data" / "tw_stock.db"))
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) FROM watchlist w
        LEFT JOIN (
            SELECT ticker, close FROM price_history
            WHERE date = (SELECT MAX(date) FROM price_history)
        ) p ON w.ticker = p.ticker
        WHERE p.close IS NULL OR p.close = 0
    """)
    missing = cur.fetchone()[0]
    conn.close()

    summary = (
        f"- 監控 11 支\n"
        f"- 現價缺失: {missing} 支\n"
        f"- 最新交易日: {today}"
    )

    # Step 4: 通知 Quinn 主動分析
    print(f"Step 3: 通知 Quinn 主動分析...")
    notify_quinn_to_analyze(0, summary)

    print(f"[{now.strftime('%H:%M:%S')}] ✅ 觸發完成，等待 Quinn 分析")
    return 0


if __name__ == "__main__":
    sys.exit(main())
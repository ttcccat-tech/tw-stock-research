#!/usr/bin/env python3
"""
老大專用 — 庫存更新 CLI
使用方式：
  python3 update_holding.py 2753 3000 179.95
  python3 update_holding.py 2241 1600 35.50    (新進場)
  python3 update_holding.py 2753 +500 178.00    (加碼 500 股)
  python3 update_holding.py 2753 -500 180.00    (減碼 500 股)
"""
import sqlite3
import sys
from pathlib import Path

REPO_DIR = Path("/var/repo/tw-stock-research")
DB = REPO_DIR / "data" / "tw_stock.db"


def update_holding(ticker, change_shares=None, new_total_shares=None,
                   change_avg_cost=None, note=None):
    """更新庫存 (支援加碼/減碼/平均成本調整)"""
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    # 取得現有庫存
    cur.execute("SELECT shares, avg_cost FROM holdings WHERE ticker=?", (ticker,))
    row = cur.fetchone()

    if row:
        old_shares, old_avg = row
    else:
        old_shares, old_avg = 0, None

    # 計算新庫存
    if new_total_shares is not None:
        new_shares = int(new_total_shares)
        new_avg = change_avg_cost if change_avg_cost else old_avg
    elif change_shares is not None:
        new_shares = old_shares + int(change_shares)
        if change_avg_cost and old_shares > 0:
            # 加碼/減碼時重算平均成本 (假設減碼以 FIFO)
            if int(change_shares) > 0:
                # 加碼
                total_cost = old_shares * old_avg + int(change_shares) * change_avg_cost
                new_avg = total_cost / new_shares
            else:
                # 減碼不變動平均成本
                new_avg = old_avg
        else:
            new_avg = change_avg_cost or old_avg
    else:
        new_shares = old_shares
        new_avg = change_avg_cost or old_avg

    if new_shares <= 0:
        # 清倉
        cur.execute("DELETE FROM holdings WHERE ticker=?", (ticker,))
        conn.commit()
        conn.close()
        print(f"🔴 已清倉 {ticker}")
        return

    cost_basis = new_shares * new_avg

    cur.execute("""
        INSERT OR REPLACE INTO holdings
        (ticker, name, shares, avg_cost, cost_basis, first_buy_date, last_updated, note)
        VALUES (?, ?, ?, ?, ?,
                COALESCE((SELECT first_buy_date FROM holdings WHERE ticker=?), date('now')),
                date('now'),
                COALESCE((SELECT note FROM holdings WHERE ticker=?), ?))
    """, (
        ticker, _get_name(ticker), new_shares, new_avg, cost_basis,
        ticker, ticker, note
    ))
    conn.commit()
    conn.close()

    print(f"✅ {ticker} 庫存更新:")
    old_avg_s = f"{old_avg:.2f}" if old_avg else "0.00"
    print(f"   舊: {old_shares} 股 @ {old_avg_s}")
    print(f"   新: {new_shares} 股 @ {new_avg:.2f} (成本 {cost_basis:,.0f})")
    if change_shares and old_shares > 0 and new_avg and old_avg:
        diff = new_avg - old_avg
        print(f"   變動: {change_shares:+,} 股, 平均成本 {'上修' if diff>0 else '下修' if diff<0 else '不變'} {abs(diff):.2f}")


def _get_name(ticker):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT name FROM watchlist WHERE ticker=?", (ticker,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else ""


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        print("\n現有庫存：")
        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        cur.execute("SELECT ticker, name, shares, avg_cost, cost_basis FROM holdings")
        for r in cur.fetchall():
            print(f"  {r[0]} {r[1]}: {r[2]:,} 股 @ {r[3]:.2f} (成本 {r[4]:,.0f})")
        conn.close()
        sys.exit(0)

    ticker = sys.argv[1]
    arg2 = sys.argv[2]

    if arg2.startswith("+") or arg2.startswith("-"):
        change_shares = int(arg2)
        change_avg_cost = float(sys.argv[3]) if len(sys.argv) > 3 else None
        update_holding(ticker, change_shares=change_shares, change_avg_cost=change_avg_cost)
    else:
        new_total = int(arg2)
        new_avg = float(sys.argv[3]) if len(sys.argv) > 3 else None
        update_holding(ticker, new_total_shares=new_total, change_avg_cost=new_avg)
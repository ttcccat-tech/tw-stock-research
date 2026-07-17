#!/usr/bin/env python3
"""
Quinn 投資監控 — Flask 後端 API + 靜態前端
提供給瀏覽器查詢:
- 監控個股清單 (現價 / Buy Zone / 目標價 / 停損價)
- 觸發訊號歷史
- 週報/月報歷史
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, send_from_directory, abort

REPO_DIR = Path("/var/repo/tw-stock-research")
DB_PATH = REPO_DIR / "data" / "tw_stock.db"
WEB_DIR = REPO_DIR / "web"

app = Flask(__name__, static_folder=str(WEB_DIR / "static"), static_url_path="/static")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ========== API ==========
@app.route("/api/watchlist")
def api_watchlist():
    """主清單 (含現價、PE、殖利率)"""
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT w.ticker, w.name, w.exchange, w.market, w.theme, w.rating,
               w.buy_min, w.buy_max, w.target, w.stop,
               p.close, p.yclose, p.change_pct, p.pe, p.yield_pct,
               p.date as price_date
        FROM watchlist w
        LEFT JOIN price_history p ON p.ticker = w.ticker
            AND p.date = (SELECT MAX(date) FROM price_history WHERE ticker = w.ticker)
        WHERE w.in_main_list = 1
        ORDER BY w.ticker
    """)
    rows = cur.fetchall()

    # 計算每支的「建議動作」
    results = []
    for r in rows:
        r = dict(r)
        close = r.get("close")
        buy_min = r.get("buy_min")
        buy_max = r.get("buy_max")
        target = r.get("target")
        stop = r.get("stop")

        action = "📊 無報價"
        action_code = "NO_DATA"
        if close:
            if stop and close <= stop:
                action = f"🚨 觸及停損 ({stop})"
                action_code = "STOP_HIT"
            elif buy_min and close <= buy_min * 1.1:
                action = "🟢 積極進場"
                action_code = "AGGRESSIVE_BUY"
            elif buy_min and close <= buy_max:
                action = "🟡 中性進場"
                action_code = "NEUTRAL_BUY"
            elif target and close >= target * 0.9:
                action = f"🎯 接近目標 ({target})"
                action_code = "NEAR_TARGET"
            elif buy_max and close > buy_max:
                action = "❌ 超出區間"
                action_code = "OVER_RANGE"
            else:
                action = "🔵 觀察中"
                action_code = "OBSERVING"
        r["action"] = action
        r["action_code"] = action_code

        # 計算距離
        if close and target:
            r["upside_to_target_pct"] = round((target - close) / close * 100, 2)
        if close and stop:
            r["downside_to_stop_pct"] = round((stop - close) / close * 100, 2)
        if close and buy_min:
            r["distance_to_buy_min_pct"] = round((buy_min - close) / close * 100, 2)

        results.append(r)
    conn.close()
    return jsonify({"count": len(results), "data": results})


@app.route("/api/alerts")
def api_alerts():
    """觸發訊號歷史"""
    limit = int(request.args.get("limit", 50))
    ticker = request.args.get("ticker", None)

    conn = get_db()
    cur = conn.cursor()
    if ticker:
        cur.execute("""
            SELECT * FROM alerts WHERE ticker = ?
            ORDER BY timestamp DESC LIMIT ?
        """, (ticker, limit))
    else:
        cur.execute("""
            SELECT * FROM alerts ORDER BY timestamp DESC LIMIT ?
        """, (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify({"count": len(rows), "data": rows})


@app.route("/api/reports")
def api_reports():
    """分析報告歷史 (週報、月報)"""
    limit = int(request.args.get("limit", 20))
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM reports ORDER BY published_at DESC LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify({"count": len(rows), "data": rows})


@app.route("/api/reports/file/<slug>")
def api_report_file(slug):
    """週報 Markdown 內容"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT file_path FROM reports WHERE slug = ?", (slug,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return abort(404)
    file_path = REPO_DIR / row["file_path"]
    if not file_path.exists():
        return abort(404)
    return send_from_directory(file_path.parent, file_path.name)


@app.route("/api/price-history/<ticker>")
def api_price_history(ticker):
    """個股價格歷史 (技術分析用)"""
    days = int(request.args.get("days", 60))
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT date, close, volume_lots, change_pct
        FROM price_history
        WHERE ticker = ?
        ORDER BY date DESC
        LIMIT ?
    """, (ticker, days))
    rows = [dict(r) for r in cur.fetchall()]
    rows.reverse()  # 由舊到新 (圖表友善)
    conn.close()
    return jsonify({"ticker": ticker, "count": len(rows), "data": rows})


@app.route("/api/summary")
def api_summary():
    """系統摘要 (首頁統計用)"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM watchlist WHERE in_main_list = 1")
    watch_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM price_history")
    price_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM alerts")
    alert_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM reports")
    report_count = cur.fetchone()[0]
    cur.execute("SELECT MAX(date) FROM price_history")
    latest_date = cur.fetchone()[0]
    cur.execute("SELECT MAX(timestamp) FROM alerts")
    latest_alert = cur.fetchone()[0]
    conn.close()
    return jsonify({
        "watchlist_count": watch_count,
        "price_history_count": price_count,
        "alerts_count": alert_count,
        "reports_count": report_count,
        "latest_price_date": latest_date,
        "latest_alert": latest_alert,
        "system_status": "🟢 正常運作",
        "last_update": datetime.now().isoformat(),
    })


# ========== 靜態頁面 ==========
@app.route("/")
def index():
    return send_from_directory(WEB_DIR, "index.html")


@app.route("/reports")
def reports_page():
    return send_from_directory(WEB_DIR, "reports.html")


if __name__ == "__main__":
    print(f"🚀 Quinn 投資監控 API 啟動")
    print(f"   DB: {DB_PATH}")
    print(f"   WEB: {WEB_DIR}")
    print(f"   http://0.0.0.0:5050")
    app.run(host="0.0.0.0", port=5050, debug=False)
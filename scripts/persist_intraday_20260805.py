import sqlite3
from pathlib import Path

conn = sqlite3.connect("data/tw_stock.db")
ts = "2026-08-05T09:35:00+08:00"
rows = [
    ("2241", "P0_DISCIPLINE", 35.15, "艾姆勒35.15，Q2財報董事會今日召開；DB仍有2,000股@34.75。延續既定風控：券商若仍有庫存，35.0-35.5反彈區全數出清，不因6月營收+125.11%延後；財報結果盤後再重評。"),
    ("4977", "DAILY_GAIN_GT5", 141.5, "眾達-KY 141.5，盤中估算+8.02%；CPO族群題材帶動且6月營收YoY轉+8.08%，但Q1仍虧、高當沖，禁止追價；原試單改等130以下且量縮再評估。"),
    ("6515", "DAILY_GAIN_GT5", 7105.0, "穎崴7105，盤中估算+8.06%；4-6月營收YoY +50.51%/+119.79%/+287.9%，基本面強但PE約134.7倍；不追高，既無持倉，等6500以下或7月營收公告後再決定。"),
    ("6412", "REVENUE_WEAK", 78.7, "群電78.7，雖在75-100 Buy Zone，但7月營收YoY -12.99%、前7月-8.4%；取消新單，等待營收連續轉正。"),
]
inserted = 0
for ticker, alert_type, price, message in rows:
    exists = conn.execute(
        "SELECT 1 FROM alerts WHERE substr(timestamp,1,10)=? AND ticker=? AND alert_type=?",
        ("2026-08-05", ticker, alert_type),
    ).fetchone()
    if not exists:
        conn.execute(
            "INSERT INTO alerts(timestamp,ticker,alert_type,price,message,discord_sent,read) VALUES(?,?,?,?,?,0,0)",
            (ts, ticker, alert_type, price, message),
        )
        inserted += 1
conn.commit()
total = conn.execute("SELECT count(*) FROM alerts WHERE substr(timestamp,1,10)=?", ("2026-08-05",)).fetchone()[0]
log = Path("logs/intraday-alerts.log")
log.parent.mkdir(exist_ok=True)
with log.open("a", encoding="utf-8") as f:
    f.write("2026-08-05 09:35 | 加權44676.43 (+3.03%), 櫃買386.52 (+3.06%)；11檔完整檢視。2241既定P0出清紀律優先；4977/6515單日估算漲逾8%不追；6412 7月營收年減12.99%取消新單；6509持倉2000股@46.97，現45.30，續抱不加碼。價格多為best_bid_estimate，以券商成交為準。\n")
print(f"inserted={inserted} alerts_total_today={total}")

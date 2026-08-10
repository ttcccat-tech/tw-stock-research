import sqlite3
from pathlib import Path

report_path = Path("reports/weekly/weekly-20260803-20260807.md").resolve()
assert report_path.exists() and report_path.stat().st_size > 10000, "weekly report missing or too small"
slug = "weekly-20260803-20260807"
values = (
    slug,
    "Quinn 週報 (2026-08-03 ~ 2026-08-07) — 結構性輪動週, 2241 出清, 6509 Buy Zone 突破",
    "weekly",
    "2026-08-09T18:00:00+08:00",
    str(report_path),
    "/api/reports/file/" + slug,
    "結構性輪動+個股事件消化週。加權穩 44K, 11 支主清單 6 漲 4 跌 1 除權息, 6509 連 2 月年增 Buy Zone 突破(+9.0%), 2241 Q2 財報 H1 虧損 4,366 萬+8/7 -6.98% 紀律出清, 2834 完成除權息。新增 6446 藥華藥(8/12 法說後 1,020-1,050)、2885 元大金、0050 定投為主動提案; 觀察池 3008 大立光升 WATCH。",
    "2753,1734,6509,2834,3479,6412,2241,4977,6472,6409,6515,6446,2885,0050,3008,2330",
    "weekly,quinn,selection,structural-rotation,watchlist,proactive,discipline",
)
conn = sqlite3.connect("data/tw_stock.db")
conn.execute(
    """INSERT INTO reports
       (slug,title,report_type,published_at,file_path,file_url,summary,tickers,tags)
       VALUES(?,?,?,?,?,?,?,?,?)
       ON CONFLICT(slug) DO UPDATE SET
       title=excluded.title,report_type=excluded.report_type,
       published_at=excluded.published_at,file_path=excluded.file_path,
       file_url=excluded.file_url,summary=excluded.summary,
       tickers=excluded.tickers,tags=excluded.tags""",
    values,
)
conn.commit()
result = conn.execute(
    "select id,slug,report_type,file_path from reports where slug=?", (slug,)
).fetchone()
print("Inserted:", result)
print("Slug:", slug)
print("Tickers:", values[7])
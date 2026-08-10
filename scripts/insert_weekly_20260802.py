import sqlite3
from pathlib import Path

report_path = Path("reports/weekly/weekly-20260727-20260731.md").resolve()
assert report_path.exists() and report_path.stat().st_size > 10000
slug = "weekly-20260727-20260731"
values = (
    slug,
    "Quinn 週報 (2026-07-27 ~ 2026-07-31)",
    "weekly",
    "2026-08-02T18:00:00+08:00",
    str(report_path),
    "/api/reports/file/" + slug,
    "台股歷史級危機後暴力修復，11 支中 8 支週線收黑。2241 於 8/5 最後驗證，若獲利未改善即移除；6509 守 42 至 8/10 營收驗證。新增優先關注 6446 與 2885，0050 採核心定投。",
    "2753,1734,6509,2834,3479,6412,2241,4977,6472,6409,6515,6446,2885,0050,3008,6187",
    "weekly,quinn,selection,crisis-recovery,watchlist,proactive",
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
print(conn.execute("select id,slug,report_type,file_path from reports where slug=?", (slug,)).fetchone())

import sqlite3
from pathlib import Path

report_path = Path("reports/weekly/weekly-20260810-20260814.md").resolve()
assert report_path.exists() and report_path.stat().st_size > 10000, "weekly report missing or too small"
slug = "weekly-20260810-20260814"
values = (
    slug,
    "Quinn 週報 (2026-08-10 ~ 2026-08-14) — 月營收 + Q2 財報雙重驗證週, 6509 EPS 2.16 修復確立, 2241 出清, 5904 漲停後消化",
    "weekly",
    "2026-08-16T18:00:00+08:00",
    str(report_path),
    "/api/reports/file/" + slug,
    "月營收+ Q2財報雙重驗證週。加權 8/13 衝高約 45,962 創波段高, 8/14 收 45,811 (-0.46%) 拉回, 11支原始主清單6漲4跌1持平, 4977 眾達 +7.87% 三重確認達成, 3479 安勤 -6.5% 個股孤立弱勢, 6412 群電 +1.15% 但月營收 -12.99% 結構轉弱, 1734 杏輝 -0.16% 月營收結構轉弱, 6509 H1 EPS 2.16 大幅優於預期 Buy Zone 突破邏輯完整(評分75→76), 5904 寶雅拆股後基本面+34.7%但漲停後-9.3%技術消化(Pitfall 241), 2241 老大指令跌破40出清生效。新主動提案: 6446藥華藥(84分第一順位) + 3008大立光(79分升級新增) + 2885元大金(78分) + 0050核心定投(76分)。清單容量上限12支, 建議本週新增1支, 其餘保留 WATCH。",
    "2753,1734,6509,2834,3479,6412,4977,6472,6409,6515,5904,6446,3008,2885,0050,2330,2241(保留中)",
    "weekly,quinn,selection,structural-rotation,monthly-revenue-verification,q2-financials,watchlist,proactive,discipline",
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
import sqlite3
from pathlib import Path

report_path = Path("reports/weekly/weekly-20260824-20260828.md").resolve()
assert report_path.exists() and report_path.stat().st_size > 10000, "weekly report missing or too small"
slug = "weekly-20260824-20260828"
values = (
    slug,
    "Quinn 週報 (2026-08-24 ~ 2026-08-28) — 內需轉弱訊號首現 + 4977 漲停翻多 + 2241 法說會基本面翻正 + 5904 SOP 第5日觸發",
    "weekly",
    "2026-08-30T18:00:00+08:00",
    str(report_path),
    "/api/reports/file/" + slug,
    "內需轉弱訊號首現 + 4977 漲停翻多 + 2241 法說會基本面翻正 + 5904 SOP 第5日觸發。加權 8/28 收 46,331.45 (+356.23, +0.77%) 站回波段高點, 14支主清單6漲7跌1持平(最高4977 +14.29%, 最低1734 -5.38%), 2753 內需轉弱訊號首現(-4.26%), 2241 H1法說會Q2毛利率由-5.4%翻正至9.3%+800G OSFP通過北美驗證, 原始跌破40出清指令背景已過時, 5904 SOP累計第5日觸發, 6472 8/25高470後健康回吐-4.40%。新主動提案: 6446藥華藥(84分第一順位) + 3008大立光(79分升級) + 2330台積電(80分升評) + 2885元大金(78分) + 0050核心定投(76分)。清單容量上限14支, 建議本週新增1支(6446第一), 其餘保留WATCH。2753 8/29若跌破178老大可評估減倉1,000股。",
    "2753,1734,6509,2834,3479,6412,4977,2241(保留中),6472,6409,6515,2330,5904,7780,6446,3008,2885,0050",
    "weekly,quinn,selection,structural-rotation,monthly-revenue-verification,domestic-demand-weak-signal,ai-rotation,cpo,cdmo,watchlist,proactive,discipline",
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

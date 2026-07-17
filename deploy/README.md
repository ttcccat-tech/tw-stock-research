# Quinn 容器化部署指南

## 🎯 目標
將 Quinn 投資分析師系統容器化部署，支援本機與雲端兩種模式。

## 📦 架構

```
┌────────────────────────────────────────┐
│  Cloudflare Tunnel (選用)               │  ← HTTPS + DDoS 防護
└──────────────┬─────────────────────────┘
               │
┌──────────────▼─────────────────────────┐
│  quinn-web (Docker 容器)               │
│  ├── Flask web (port 5050)            │
│  ├── Cron daemon (容器內)               │
│  └── Python 3.11 + 依賴                │
└──────┬─────────┬──────────┬─────────────┘
       │         │          │
       ▼         ▼          ▼
  ./data/   ./reports/  ./price-history/
  (SQLite)  (MD reports) (CSV 歷史)
  ./logs/
```

## 🚀 快速啟動 (本機模式)

```bash
# 1. 構建並啟動
cd /var/repo/tw-stock-research
docker-compose up -d

# 2. 查看狀態
docker-compose ps
docker-compose logs -f quinn-web

# 3. 訪問
http://localhost:5050

# 4. 停止
docker-compose down
```

## 🌐 對外訪問 (Cloudflare Tunnel)

```bash
# 設定環境變數
echo "CLOUDFLARE_TUNNEL_TOKEN=eyJh..." > .env

# 啟動 (含 tunnel profile)
docker-compose --profile tunnel up -d
```

完整 Tunnel 設定: [deploy/CLOUDFLARE-TUNNEL.md](./deploy/CLOUDFLARE-TUNNEL.md)

## 📋 容器內自動執行的 Cron Jobs

| 時間 | 任務 | Log |
|------|------|-----|
| 08:55 平日 | 啟動盤中監控守護 | `logs/daemon.log` |
| 13:30 平日 | 抓收盤價 + 寫入 DB | `logs/fetch.log` |
| 13:40 平日 | 盤後分析 + Discord 報告 | `logs/postmarket.log` |
| 14:00 平日 | DB 同步 | `logs/db_init.log` |
| 18:00 週日 | 自動產生週報 | `logs/weekly.log` |

## 🔧 故障排查

```bash
# 查看容器 log
docker-compose logs -f quinn-web

# 進入容器
docker exec -it quinn-tw-stock bash

# 手動跑腳本
docker exec -it quinn-tw-stock python3 scripts/fetch_prices.py

# 查看 cron log
docker exec -it quinn-tw-stock tail -f /app/logs/fetch.log
```

## 💾 資料備份

```bash
# 備份 SQLite DB
docker exec quinn-tw-stock cp /app/data/tw_stock.db /tmp/backup.db
docker cp quinn-tw-stock:/tmp/backup.db ./backup-$(date +%Y%m%d).db

# 或直接備份 volume 目錄
tar -czf backup-$(date +%Y%m%d).tar.gz data/ reports/ price-history/ logs/
```

## 🚀 升級到雲端 (未來)

老大您目前是本機模式，未來如要 24/7 雲端運行，建議:

| 平台 | 費用 | 難度 | 適合 |
|------|------|------|------|
| **Fly.io** | 免費額度小，需付費 | 中 | 雲端新手 |
| **Render** | 免費方案 | 低 | 個人小流量 |
| **Railway** | 5 USD/月 | 低 | 中小應用 |
| **自架 VPS (Hetzner / DigitalOcean)** | 5-10 USD/月 | 高 | 完全掌控 |

Quinn 建議: 先用本機 + Cloudflare Tunnel 跑幾週，穩定後再決定是否上雲。
# Cloudflare Tunnel 設定 (本地對外訪問最簡方案)

## 為什麼用 Cloudflare Tunnel?

1. **免費 HTTPS** — 不用申請 SSL 憑證
2. **零端口暴露** — 主機防火牆完全不用開 80/443 端口
3. **DDoS 保護** — Cloudflare CDN 自動擋攻擊
4. **Quick Tunnel 模式** — 不用設定 Cloudflare 帳號，5 分鐘搞定

## 🚀 方案 A: Quick Tunnel (5 分鐘搞定)

```bash
# 在容器主機或容器內執行
cloudflared tunnel --url http://localhost:5050
# 會得到一個 https://xxx.trycloudflare.com 網址
```

**優點**: 不需帳號、不需設定  
**缺點**: 網址每次重啟會變

## 🔒 方案 B: 固定網址 (推薦 — 老大可以分享給自己/家人)

### 步驟:
1. 註冊 Cloudflare 帳號 (免費)
2. 把您的網域 (例如 stock.terence.tw) 加入 Cloudflare
3. 建立 Tunnel:
   - Cloudflare Dashboard → Zero Trust → Networks → Tunnels
   - 建立 Tunnel → 複製 Token
4. 設定 `.env`:
   ```
   CLOUDFLARE_TUNNEL_TOKEN=eyJhIjoixxxxx...
   ```
5. 啟動:
   ```bash
   docker-compose --profile tunnel up -d
   ```

### 子網域路由設定:
在 Cloudflare Dashboard → Tunnel → Configure → Public Hostname:
- Subdomain: stock
- Domain: terence.tw
- Service: http://quinn-web:5050

完成後訪問: https://stock.terence.tw 即可從外面安全訪問

## 📱 訪問權限管理

老大您說「**頻道不可能分享給其他人**」，Quinn 提供三層保護:

1. **Cloudflare Access** (推薦) — 在 Cloudflare Dashboard 設定 Email OTP 認證
   - 只有您的 email (terrence_19633) 可以登入
   - 想分享家人時加他們的 email
2. **Flask Basic Auth** (簡單) — 直接在 web 加密碼保護
3. **隱私 Tunnel URL** (基本) — 不公開網址，靠 URL 隱蔽性

## ⚙️ 本機 vs 雲端部署比較

| 項目 | 本機 + Tunnel | 雲端 (Fly.io / Render) |
|------|--------------|----------------------|
| **費用** | 主機電費 + 網路 | 免費 (限制資源) |
| **訪問速度** | 看老大主機網速 | 雲端較快 |
| **資料掌控** | 100% 本地 | 雲端託管 |
| **備份** | 自己備份 | 雲端自動備份 |
| **維運** | 主機要開著 | 雲端 24/7 |
| **推薦** | 老大已有主機 ✅ | 需付費升級 |

Quinn 推薦**本機 + Cloudflare Quick Tunnel** 作為 MVP，穩定後升級到固定網址。
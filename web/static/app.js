// Quinn 投資監控 - 前端邏輯

const API_BASE = '';

// ========== 首頁：監控清單 ==========
async function loadWatchlist() {
    const container = document.getElementById('watchlist-table');
    container.innerHTML = '<div class="loading">載入中...</div>';

    try {
        const resp = await fetch(`${API_BASE}/api/watchlist`);
        const data = await resp.json();
        renderWatchlist(data.data);
        updateLastUpdate();
    } catch (err) {
        container.innerHTML = `<div class="loading">❌ 載入失敗: ${err.message}</div>`;
    }
}

function renderWatchlist(rows) {
    const html = `
        <table>
            <thead>
                <tr>
                    <th>代碼</th>
                    <th>名稱</th>
                    <th>評等</th>
                    <th>現價</th>
                    <th>漲跌</th>
                    <th>庫存</th>
                    <th>平均成本</th>
                    <th>損益%</th>
                    <th>Buy Zone</th>
                    <th>距目標</th>
                    <th>距停損</th>
                    <th>目標價</th>
                    <th>停損價</th>
                    <th>建議動作</th>
                </tr>
            </thead>
            <tbody>
                ${rows.map(r => renderRow(r)).join('')}
            </tbody>
        </table>
    `;
    document.getElementById('watchlist-table').innerHTML = html;
}

function renderRow(r) {
    const ratingClass = r.rating?.includes('Buy') ? 'badge-green' :
                        r.rating?.includes('Hold') ? 'badge-yellow' :
                        r.rating?.includes('Watch') ? 'badge-blue' : 'badge-gray';

    const priceClass = r.change_pct > 0 ? 'up' : r.change_pct < 0 ? 'down' : '';
    const changePct = r.change_pct ? (r.change_pct > 0 ? `+${r.change_pct}%` : `${r.change_pct}%`) : '–';

    const upsideStr = r.upside_to_target_pct != null
        ? `<span class="target-up">${r.upside_to_target_pct > 0 ? '+' : ''}${r.upside_to_target_pct}%</span>`
        : '–';

    const stopStr = r.downside_to_stop_pct != null
        ? `<span class="stop-warn">${r.downside_to_stop_pct}%</span>`
        : '–';

    // === 庫存欄位渲染 ===
    const hasHolding = r.holdings_shares && r.holdings_shares > 0;
    const sharesStr = hasHolding ? r.holdings_shares.toLocaleString() : '–';
    const costStr = hasHolding ? r.holdings_avg_cost.toFixed(2) : '–';

    let pnlStr = '–';
    let pnlClass = '';
    if (hasHolding && r.holdings_unrealized_pct != null) {
        const pct = r.holdings_unrealized_pct;
        pnlStr = `${pct > 0 ? '+' : ''}${pct}%`;
        if (pct >= 0) pnlClass = 'up';
        else pnlClass = 'down';
    }

    return `
        <tr>
            <td><span class="ticker">${r.ticker}</span></td>
            <td><span class="name">${r.name}</span><br><span class="last-update">${r.theme || ''}</span></td>
            <td><span class="badge ${ratingClass}">${r.rating || '–'}</span></td>
            <td><span class="price ${priceClass}">${r.close ? r.close.toFixed(2) : '–'}</span></td>
            <td class="${priceClass}">${changePct}</td>
            <td class="${hasHolding ? 'holding-yes' : 'holding-no'}">${sharesStr}</td>
            <td>${costStr}</td>
            <td class="${pnlClass}">${pnlStr}</td>
            <td class="buy-zone">${r.buy_min}–${r.buy_max}</td>
            <td>${upsideStr}</td>
            <td>${stopStr}</td>
            <td><strong>${r.target || '–'}</strong></td>
            <td>${r.stop || '–'}</td>
            <td class="action-cell">${r.action}</td>
        </tr>
    `;
}

// ========== 系統摘要 ==========
async function loadSummary() {
    try {
        const resp = await fetch(`${API_BASE}/api/summary`);
        const data = await resp.json();
        const html = `
            <div class="summary-card">
                <div class="label">📊 監控標的</div>
                <div class="value">${data.watchlist_count}</div>
                <div class="sub">支主清單</div>
            </div>
            <div class="summary-card">
                <div class="label">💾 歷史紀錄</div>
                <div class="value">${data.price_history_count}</div>
                <div class="sub">筆每日收盤</div>
            </div>
            <div class="summary-card">
                <div class="label">🔔 觸發訊號</div>
                <div class="value">${data.alerts_count}</div>
                <div class="sub">個歷史紀錄</div>
            </div>
            <div class="summary-card">
                <div class="label">📋 分析報告</div>
                <div class="value">${data.reports_count}</div>
                <div class="sub">份歷史報告</div>
            </div>
            <div class="summary-card">
                <div class="label">🕐 最新交易日</div>
                <div class="value" style="font-size:18px">${data.latest_price_date || '–'}</div>
                <div class="sub">系統狀態: ${data.system_status}</div>
            </div>
        `;
        document.getElementById('summary').innerHTML = html;
    } catch (err) {
        document.getElementById('summary').innerHTML = `<div class="summary-card">❌ 載入失敗</div>`;
    }
}

function updateLastUpdate() {
    const now = new Date().toLocaleString('zh-TW');
    document.getElementById('last-update').textContent = `最後更新: ${now}`;
}

// ========== 報告列表頁 ==========
async function loadReports() {
    const container = document.getElementById('reports-list');
    container.innerHTML = '<div class="loading">載入中...</div>';

    try {
        const resp = await fetch(`${API_BASE}/api/reports?limit=50`);
        const data = await resp.json();
        renderReports(data.data);
    } catch (err) {
        container.innerHTML = `<div class="loading">❌ 載入失敗: ${err.message}</div>`;
    }
}

function renderReports(rows) {
    if (rows.length === 0) {
        container.innerHTML = '<div class="loading">尚無報告</div>';
        return;
    }
    const html = rows.map(r => `
        <div class="summary-card" style="margin-bottom:12px">
            <div style="display:flex; justify-content:space-between">
                <div>
                    <div style="font-size:16px; font-weight:600; color:#f1f5f9">${r.title}</div>
                    <div class="last-update">${new Date(r.published_at).toLocaleString('zh-TW')} · ${r.report_type}</div>
                    <div class="last-update">${r.summary || ''}</div>
                    ${r.tags ? `<div class="last-update">🏷 ${r.tags}</div>` : ''}
                </div>
                <a href="${r.file_url}" target="_blank" class="refresh-btn">📄 檢視報告</a>
            </div>
        </div>
    `).join('');
    document.getElementById('reports-list').innerHTML = html;
}

// ========== 初始化 ==========
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('watchlist-table')) {
        loadSummary();
        loadWatchlist();
    }
    if (document.getElementById('reports-list')) {
        loadReports();
    }
});
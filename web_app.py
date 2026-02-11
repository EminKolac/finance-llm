"""
Web Interface for Finance LLM Assistant
A Flask-based web UI with dynamic configuration for BIST stocks
"""

from flask import Flask, render_template_string, request, jsonify, session
import os
import json
from dotenv import load_dotenv
from yahoo_finance import YahooFinanceAPI, execute_api_call
from llm_interface import FinanceLLM
from portfolio_data import get_all_dashboard_data

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

# Store instances per session
assistants = {}

# Cache dashboard data (loaded once on startup)
_dashboard_data = None

def get_cached_dashboard_data():
    global _dashboard_data
    if _dashboard_data is None:
        _dashboard_data = get_all_dashboard_data()
    return _dashboard_data

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Finance LLM - BIST Stock Assistant</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #e0e0e0;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        header {
            text-align: center;
            padding: 20px 0;
            border-bottom: 1px solid #333;
            margin-bottom: 20px;
        }
        h1 {
            color: #00d4ff;
            font-size: 2em;
        }
        .subtitle { color: #888; margin-top: 5px; }

        .grid {
            display: grid;
            grid-template-columns: 300px 1fr;
            gap: 20px;
        }

        .sidebar {
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 20px;
        }
        .sidebar h2 {
            color: #00d4ff;
            font-size: 1.1em;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid #333;
        }

        .config-section { margin-bottom: 25px; }
        label {
            display: block;
            margin-bottom: 5px;
            color: #aaa;
            font-size: 0.9em;
        }
        input, select, textarea {
            width: 100%;
            padding: 10px;
            border: 1px solid #333;
            border-radius: 6px;
            background: #1a1a2e;
            color: #e0e0e0;
            font-size: 0.95em;
        }
        input:focus, select:focus, textarea:focus {
            outline: none;
            border-color: #00d4ff;
        }
        textarea { resize: vertical; min-height: 150px; font-family: monospace; }

        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.95em;
            transition: all 0.2s;
        }
        .btn-primary {
            background: #00d4ff;
            color: #1a1a2e;
        }
        .btn-primary:hover { background: #00b8e6; }
        .btn-secondary {
            background: #333;
            color: #e0e0e0;
        }
        .btn-secondary:hover { background: #444; }

        .main-content {
            display: flex;
            flex-direction: column;
        }

        /* Tabs */
        .tab-bar {
            display: flex;
            gap: 0;
            margin-bottom: 0;
        }
        .tab-btn {
            padding: 12px 24px;
            background: rgba(255,255,255,0.03);
            border: 1px solid #333;
            border-bottom: none;
            border-radius: 12px 12px 0 0;
            color: #888;
            cursor: pointer;
            font-size: 0.95em;
            transition: all 0.2s;
        }
        .tab-btn.active {
            background: rgba(255,255,255,0.05);
            color: #00d4ff;
            border-color: #00d4ff;
            border-bottom: 2px solid rgba(255,255,255,0.05);
        }
        .tab-btn:hover { color: #e0e0e0; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }

        .chat-container {
            flex: 1;
            background: rgba(255,255,255,0.05);
            border-radius: 0 12px 12px 12px;
            display: flex;
            flex-direction: column;
            min-height: 500px;
        }

        .chat-messages {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
            max-height: 400px;
        }

        .message {
            margin-bottom: 15px;
            padding: 12px 16px;
            border-radius: 12px;
            max-width: 85%;
            white-space: pre-wrap;
        }
        .message.user {
            background: #00d4ff;
            color: #1a1a2e;
            margin-left: auto;
        }
        .message.assistant {
            background: #2a2a4a;
        }
        .message.system {
            background: #333;
            color: #888;
            text-align: center;
            max-width: 100%;
            font-size: 0.9em;
        }

        .chat-input {
            padding: 20px;
            border-top: 1px solid #333;
            display: flex;
            gap: 10px;
        }
        .chat-input input {
            flex: 1;
        }

        .portfolio-card {
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 20px;
            margin-top: 20px;
        }
        .portfolio-card h3 {
            color: #00d4ff;
            margin-bottom: 15px;
        }
        .stock-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
            gap: 10px;
        }
        .stock-item {
            background: #1a1a2e;
            padding: 10px;
            border-radius: 8px;
            text-align: center;
        }
        .stock-symbol { font-weight: bold; color: #00d4ff; }
        .stock-price { font-size: 1.1em; margin: 5px 0; }
        .stock-change { font-size: 0.9em; }
        .stock-change.positive { color: #00ff88; }
        .stock-change.negative { color: #ff4466; }

        .loading {
            display: none;
            text-align: center;
            padding: 20px;
        }
        .loading.active { display: block; }

        /* Dashboard styles */
        .dashboard-container {
            background: rgba(255,255,255,0.05);
            border-radius: 0 12px 12px 12px;
            padding: 20px;
            min-height: 500px;
        }

        .metric-cards {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
            gap: 12px;
            margin-bottom: 20px;
        }
        .metric-card {
            background: #1a1a2e;
            border-radius: 10px;
            padding: 14px;
            border: 1px solid #333;
            transition: transform 0.15s;
        }
        .metric-card:hover { transform: translateY(-2px); }
        .metric-card .card-label {
            font-size: 0.72em;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 6px;
        }
        .metric-card .card-value {
            font-size: 1.4em;
            font-weight: 700;
        }
        .metric-card .card-sub {
            font-size: 0.78em;
            color: #888;
            margin-top: 4px;
        }
        .positive { color: #00ff88; }
        .negative { color: #ff4466; }
        .neutral { color: #00d4ff; }

        .section-panel {
            background: #1a1a2e;
            border: 1px solid #333;
            border-radius: 12px;
            margin-bottom: 16px;
            overflow: hidden;
        }
        .section-panel .section-title {
            padding: 14px 18px;
            border-bottom: 1px solid #333;
            color: #00d4ff;
            font-size: 1em;
            font-weight: 600;
        }
        .section-panel .section-body { padding: 18px; }

        .chart-box { position: relative; width: 100%; height: 320px; }
        .chart-box canvas { width: 100% !important; height: 100% !important; }

        .two-col-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
        }

        /* Holdings table */
        .holdings-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.82em;
        }
        .holdings-table th {
            background: rgba(255,255,255,0.05);
            color: #888;
            text-align: left;
            padding: 10px 10px;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.78em;
            letter-spacing: 0.5px;
            border-bottom: 2px solid #333;
            position: sticky;
            top: 0;
        }
        .holdings-table td {
            padding: 8px 10px;
            border-bottom: 1px solid #2a2a4a;
            white-space: nowrap;
        }
        .holdings-table tr:hover td { background: rgba(255,255,255,0.03); }
        .holdings-table .total-row td {
            background: rgba(0,212,255,0.08);
            font-weight: 700;
            border-top: 2px solid #00d4ff;
            color: #00d4ff;
        }
        .table-scroll { max-height: 450px; overflow: auto; }

        /* Risk pie */
        .risk-chart-box { position: relative; width: 100%; height: 220px; }

        /* Insights */
        .insight-item {
            background: #1a1a2e;
            border-radius: 8px;
            padding: 12px 16px;
            margin-bottom: 8px;
            border-left: 3px solid #00d4ff;
        }
        .insight-item.success { border-left-color: #00ff88; }
        .insight-item.warning { border-left-color: #ffaa33; }
        .insight-item.danger { border-left-color: #ff4466; }
        .insight-item h4 { font-size: 0.88em; margin-bottom: 4px; }
        .insight-item p { font-size: 0.82em; color: #888; line-height: 1.5; }

        /* Export button */
        .export-btn {
            padding: 8px 16px;
            background: #00ff88;
            color: #1a1a2e;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.82em;
            font-weight: 600;
        }
        .export-btn:hover { opacity: 0.85; }

        @media (max-width: 900px) {
            .grid { grid-template-columns: 1fr; }
            .two-col-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Finance LLM Assistant</h1>
            <p class="subtitle">TVF Portfolio Dashboard & BIST Stock Analysis with AI</p>
        </header>

        <div class="grid">
            <aside class="sidebar">
                <div class="config-section">
                    <h2>API Configuration</h2>
                    <label>API Key</label>
                    <input type="password" id="apiKey" placeholder="Enter your API key">

                    <label style="margin-top:10px">Base URL</label>
                    <select id="baseUrl">
                        <option value="https://api.openai.com/v1">OpenAI</option>
                        <option value="https://api.groq.com/openai/v1">Groq</option>
                        <option value="https://api.together.xyz/v1">Together AI</option>
                        <option value="http://localhost:1234/v1">Local (LM Studio)</option>
                        <option value="custom">Custom URL</option>
                    </select>
                    <input type="text" id="customUrl" placeholder="Custom API URL" style="display:none; margin-top:10px">

                    <label style="margin-top:10px">Model</label>
                    <input type="text" id="model" value="gpt-4o-mini" placeholder="Model name">
                </div>

                <div class="config-section">
                    <h2>System Prompt</h2>
                    <textarea id="systemPrompt" placeholder="Enter custom system prompt...">You are a helpful financial assistant for Turkish stocks (BIST).

Your tickers: HALKB, TRENJ, TRMET, TRALT, TCELL, THYAO, TTKOM, TURSG, VAKBN, KRDMD

To fetch data, use:
```json
{"function": "get_price", "parameters": {"ticker": "THYAO"}}
```

Available functions:
- get_stock_info: Get comprehensive stock information
- get_price: Get current price
- get_historical_data: Get price history (period: 1d,5d,1mo,3mo,6mo,1y)
- get_portfolio_summary: Get portfolio overview
- compare_stocks: Compare multiple stocks

Provide clear analysis. This is not financial advice.</textarea>
                </div>

                <button class="btn btn-primary" onclick="initializeChat()" style="width:100%">
                    Initialize / Update Config
                </button>
            </aside>

            <main class="main-content">
                <!-- Tab Bar -->
                <div class="tab-bar">
                    <button class="tab-btn active" onclick="switchTab('dashboard', this)">Dashboard</button>
                    <button class="tab-btn" onclick="switchTab('chat', this)">AI Chat</button>
                </div>

                <!-- Dashboard Tab -->
                <div class="tab-content active" id="tab-dashboard">
                    <div class="dashboard-container">
                        <!-- Metric Cards -->
                        <div class="metric-cards" id="metricCards"></div>

                        <!-- Charts Row -->
                        <div class="two-col-grid">
                            <div class="section-panel">
                                <div class="section-title">Indexed Performance (Base 100, USD)</div>
                                <div class="section-body">
                                    <div class="chart-box"><canvas id="indexedChart"></canvas></div>
                                </div>
                            </div>
                            <div class="section-panel">
                                <div class="section-title">Drawdown from Peak (USD)</div>
                                <div class="section-body">
                                    <div class="chart-box"><canvas id="drawdownChart"></canvas></div>
                                </div>
                            </div>
                        </div>

                        <!-- Holdings Table -->
                        <div class="section-panel">
                            <div class="section-title" style="display:flex;justify-content:space-between;align-items:center">
                                <span>Holdings</span>
                                <button class="export-btn" onclick="exportToSheets()">Export to Google Sheets</button>
                            </div>
                            <div class="section-body" style="padding:0 18px 18px">
                                <div class="table-scroll">
                                    <table class="holdings-table">
                                        <thead>
                                            <tr>
                                                <th>Ticker</th><th>Sector</th><th>Inv. Date</th>
                                                <th>Inv. Price ($)</th><th>Cur. Price ($)</th>
                                                <th>TVF %</th><th>Invested ($)</th><th>Current ($)</th>
                                                <th>Dividends ($)</th><th>Return</th><th>CAGR</th>
                                                <th>Beta</th><th>Sharpe</th><th>Sortino</th>
                                            </tr>
                                        </thead>
                                        <tbody id="holdingsBody"></tbody>
                                    </table>
                                </div>
                            </div>
                        </div>

                        <!-- Risk & Insights Row -->
                        <div class="two-col-grid">
                            <div class="section-panel">
                                <div class="section-title">Risk Decomposition</div>
                                <div class="section-body">
                                    <div class="risk-chart-box"><canvas id="riskPieChart"></canvas></div>
                                    <div class="table-scroll" style="max-height:220px;margin-top:12px">
                                        <table class="holdings-table">
                                            <thead>
                                                <tr><th>Ticker</th><th>Sector</th><th>Weight %</th><th>Beta</th><th>Std Dev %</th><th>Vol Contrib %</th></tr>
                                            </thead>
                                            <tbody id="riskBody"></tbody>
                                        </table>
                                    </div>
                                </div>
                            </div>
                            <div class="section-panel">
                                <div class="section-title">Key Insights</div>
                                <div class="section-body" id="insightsContainer"></div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Chat Tab -->
                <div class="tab-content" id="tab-chat">
                    <div class="chat-container">
                        <div class="chat-messages" id="chatMessages">
                            <div class="message system">
                                Configure your API settings and click "Initialize" to start chatting.
                            </div>
                        </div>
                        <div class="loading" id="loading">
                            <p>Processing...</p>
                        </div>
                        <div class="chat-input">
                            <input type="text" id="userInput" placeholder="Ask about your BIST stocks..."
                                   onkeypress="if(event.key==='Enter')sendMessage()">
                            <button class="btn btn-primary" onclick="sendMessage()">Send</button>
                        </div>
                    </div>

                    <div class="portfolio-card">
                        <h3>Portfolio - BIST Stocks</h3>
                        <div class="stock-grid" id="portfolioGrid">
                            <p style="color:#888">Click "Load Portfolio" to fetch current prices</p>
                        </div>
                        <button class="btn btn-secondary" onclick="loadPortfolio()" style="margin-top:15px">
                            Load Portfolio
                        </button>
                    </div>
                </div>
            </main>
        </div>
    </div>

    <script>
        // ========== DASHBOARD DATA ==========
        const D = DASHBOARD_DATA_PLACEHOLDER;

        // ========== TAB SWITCHING ==========
        function switchTab(tab, btn) {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById('tab-' + tab).classList.add('active');
        }

        // ========== TOGGLE CUSTOM URL ==========
        document.getElementById('baseUrl').addEventListener('change', function() {
            document.getElementById('customUrl').style.display =
                this.value === 'custom' ? 'block' : 'none';
        });

        function getBaseUrl() {
            const select = document.getElementById('baseUrl');
            return select.value === 'custom'
                ? document.getElementById('customUrl').value
                : select.value;
        }

        // ========== INIT ON LOAD ==========
        document.addEventListener('DOMContentLoaded', () => {
            renderMetricCards();
            renderHoldings();
            renderIndexedChart();
            renderDrawdownChart();
            renderRiskDecomposition();
            renderInsights();
        });

        // ========== METRIC CARDS ==========
        function renderMetricCards() {
            const t = D.totals;
            const retPct = t.total_return_pct;
            const retClass = retPct >= 0 ? 'positive' : 'negative';

            // Weighted avg CAGR
            let sumCW = 0, sumW = 0;
            D.holdings.forEach(h => { sumCW += h.cagr * h.current_value; sumW += h.current_value; });
            const avgCagr = sumW > 0 ? sumCW / sumW : 0;
            const cagrClass = avgCagr >= 0 ? 'positive' : 'negative';

            const sharpeClass = t.portfolio_sharpe >= 1 ? 'positive' : t.portfolio_sharpe >= 0 ? 'neutral' : 'negative';
            const sortinoClass = t.portfolio_sortino >= 1 ? 'positive' : t.portfolio_sortino >= 0 ? 'neutral' : 'negative';

            const xu = D.xu100_usd;
            const cards = [
                { label: 'Total Return (USD)', value: retPct.toFixed(1) + '%', cls: retClass, sub: 'Invested $' + fmtB(t.total_investment) },
                { label: 'Total Gain (USD)', value: '$' + fmtB(t.total_gain), cls: 'neutral', sub: 'Dividends: $' + fmtB(t.total_dividends) },
                { label: 'Wtd Avg CAGR', value: avgCagr.toFixed(1) + '%', cls: cagrClass },
                { label: 'Portfolio Beta', value: t.portfolio_beta !== null ? t.portfolio_beta.toFixed(2) : 'N/A', cls: 'neutral', sub: 'vs XU100' },
                { label: 'Sharpe Ratio', value: t.portfolio_sharpe !== null ? t.portfolio_sharpe.toFixed(2) : 'N/A', cls: sharpeClass },
                { label: 'Sortino Ratio', value: t.portfolio_sortino !== null ? t.portfolio_sortino.toFixed(2) : 'N/A', cls: sortinoClass },
                { label: 'Volatility (Ann.)', value: t.portfolio_std !== null ? t.portfolio_std.toFixed(1) + '%' : 'N/A', cls: 'neutral' },
                { label: 'Holdings', value: t.num_holdings, cls: 'neutral', sub: [...new Set(D.holdings.map(h => h.sector))].length + ' sectors' },
                { label: 'XU100 (TRY)', value: xu.xu100_try.toLocaleString(), cls: 'neutral' },
                { label: 'XU100 (USD)', value: xu.xu100_usd.toLocaleString(), cls: 'positive' },
                { label: 'USD/TRY', value: xu.usdtry.toFixed(2), cls: 'neutral' },
            ];

            const container = document.getElementById('metricCards');
            container.innerHTML = cards.map(c =>
                `<div class="metric-card">
                    <div class="card-label">${c.label}</div>
                    <div class="card-value ${c.cls}">${c.value}</div>
                    ${c.sub ? '<div class="card-sub">' + c.sub + '</div>' : ''}
                </div>`
            ).join('');
        }

        // ========== HOLDINGS TABLE ==========
        function renderHoldings() {
            const body = document.getElementById('holdingsBody');
            let html = '';
            D.holdings.forEach(h => {
                html += `<tr>
                    <td><strong style="color:#00d4ff">${h.ticker}</strong></td>
                    <td>${h.sector}</td>
                    <td>${h.investment_date}</td>
                    <td>$${h.inv_price_usd.toFixed(3)}</td>
                    <td>$${h.cur_price_usd.toFixed(3)}</td>
                    <td>${h.shareholding_pct.toFixed(1)}%</td>
                    <td>$${fmtM(h.investment_amount)}</td>
                    <td>$${fmtM(h.current_value)}</td>
                    <td>$${fmtM(h.dividends_usd)}</td>
                    <td class="${h.total_return_with_div >= 0 ? 'positive' : 'negative'}">${h.total_return_with_div.toFixed(1)}%</td>
                    <td class="${h.cagr >= 0 ? 'positive' : 'negative'}">${h.cagr.toFixed(1)}%</td>
                    <td>${h.beta !== null ? h.beta.toFixed(2) : '-'}</td>
                    <td class="${(h.sharpe||0) >= 1 ? 'positive' : (h.sharpe||0) < 0 ? 'negative' : ''}">${h.sharpe !== null ? h.sharpe.toFixed(2) : '-'}</td>
                    <td class="${(h.sortino||0) >= 1 ? 'positive' : (h.sortino||0) < 0 ? 'negative' : ''}">${h.sortino !== null ? h.sortino.toFixed(2) : '-'}</td>
                </tr>`;
            });

            // Total row
            const t = D.totals;
            let wBeta=0,wSharpe=0,wSortino=0,wCagr=0,wSum=0;
            D.holdings.forEach(h => {
                const w = h.current_value; wSum += w;
                if(h.beta!==null) wBeta += h.beta*w;
                if(h.sharpe!==null) wSharpe += h.sharpe*w;
                if(h.sortino!==null) wSortino += h.sortino*w;
                wCagr += h.cagr*w;
            });
            html += `<tr class="total-row">
                <td><strong>TOTAL</strong></td>
                <td>-</td><td>-</td><td>-</td><td>-</td><td>-</td>
                <td>$${fmtM(t.total_investment)}</td>
                <td>$${fmtM(t.total_current_value)}</td>
                <td>$${fmtM(t.total_dividends)}</td>
                <td class="${t.total_return_pct >= 0 ? 'positive' : 'negative'}">${t.total_return_pct.toFixed(1)}%</td>
                <td class="${(wCagr/wSum) >= 0 ? 'positive' : 'negative'}">${(wCagr/wSum).toFixed(1)}%</td>
                <td>${(wBeta/wSum).toFixed(2)}</td>
                <td>${(wSharpe/wSum).toFixed(2)}</td>
                <td>${(wSortino/wSum).toFixed(2)}</td>
            </tr>`;
            body.innerHTML = html;
        }

        // ========== INDEXED PERFORMANCE CHART ==========
        function renderIndexedChart() {
            const ctx = document.getElementById('indexedChart').getContext('2d');
            const perf = D.indexed_performance;
            const colors = {
                THYAO:'#ff6384', TCELL:'#36a2eb', HALKB:'#ffce56', VAKBN:'#4bc0c0',
                TTKOM:'#9966ff', TURSG:'#ff9f40', KRDMD:'#c9cbcf', TRALT:'#00ff88',
                TRMET:'#ff4466', TRENJ:'#00d4ff', XU100:'#ffffff'
            };
            const stocksToPlot = ['THYAO','TCELL','HALKB','VAKBN','TTKOM','TURSG','KRDMD','TRALT','TRMET','TRENJ','XU100'];
            const datasets = [];
            stocksToPlot.forEach(comp => {
                if (!perf[comp]) return;
                const d = perf[comp];
                const points = d.dates.map((dt, i) => ({x: dt, y: d.indexed[i]})).filter(p => p.x && p.y !== null);
                datasets.push({
                    label: comp, data: points,
                    borderColor: colors[comp] || '#888',
                    borderWidth: comp === 'THYAO' ? 2.5 : 1.5,
                    pointRadius: 0, tension: 0.1,
                    yAxisID: comp === 'THYAO' ? 'y1' : 'y',
                    borderDash: comp === 'XU100' ? [5, 3] : [],
                });
            });
            new Chart(ctx, {
                type: 'line', data: { datasets },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    interaction: { mode: 'index', intersect: false },
                    plugins: {
                        legend: { position: 'top', labels: { color: '#888', font: { size: 10 }, boxWidth: 12 } },
                        tooltip: { backgroundColor: '#1a1a2e', titleColor: '#00d4ff', bodyColor: '#e0e0e0', borderColor: '#333', borderWidth: 1 }
                    },
                    scales: {
                        x: { type: 'category', ticks: { color: '#666', maxTicksLimit: 10, font:{size:10} }, grid: { color: 'rgba(51,51,51,0.3)' } },
                        y: { position:'left', title:{display:true, text:'Others (Base 100)', color:'#888'}, ticks:{color:'#666',font:{size:10}}, grid:{color:'rgba(51,51,51,0.3)'}, min:0, max:350 },
                        y1: { position:'right', title:{display:true, text:'THYAO (Base 100)', color:'#ff6384'}, ticks:{color:'#ff6384',font:{size:10}}, grid:{drawOnChartArea:false}, min:0, max:700 }
                    }
                }
            });
        }

        // ========== DRAWDOWN CHART ==========
        function renderDrawdownChart() {
            const ctx = document.getElementById('drawdownChart').getContext('2d');
            const dd = D.drawdown;
            const colors = {
                THYAO:'#ff6384', TCELL:'#36a2eb', HALKB:'#ffce56', VAKBN:'#4bc0c0',
                TTKOM:'#9966ff', TURSG:'#ff9f40', KRDMD:'#c9cbcf', TRALT:'#00ff88',
                TRMET:'#ff4466', TRENJ:'#00d4ff'
            };
            const datasets = [];
            Object.keys(dd).forEach(comp => {
                const d = dd[comp];
                const points = d.dates.map((dt, i) => ({x: dt, y: d.drawdown[i]})).filter(p => p.x && p.y !== null);
                datasets.push({
                    label: comp + ' (Max: ' + d.max_drawdown.toFixed(1) + '%)',
                    data: points, borderColor: colors[comp] || '#888',
                    borderWidth: 1.2, pointRadius: 0, tension: 0.1, fill: false,
                });
            });
            new Chart(ctx, {
                type: 'line', data: { datasets },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    interaction: { mode: 'index', intersect: false },
                    plugins: {
                        legend: { position: 'top', labels: { color: '#888', font: { size: 10 }, boxWidth: 12 } },
                        tooltip: { backgroundColor: '#1a1a2e', titleColor: '#00d4ff', bodyColor: '#e0e0e0' }
                    },
                    scales: {
                        x: { type: 'category', ticks: { color: '#666', maxTicksLimit: 10, font:{size:10} }, grid: { color: 'rgba(51,51,51,0.3)' } },
                        y: { ticks: { color: '#666', callback: v => v+'%', font:{size:10} }, grid: { color: 'rgba(51,51,51,0.3)' } }
                    }
                }
            });
        }

        // ========== RISK DECOMPOSITION ==========
        function renderRiskDecomposition() {
            const risk = D.risk_decomposition;
            const sectorData = {};
            risk.stocks.forEach(s => {
                if (!sectorData[s.sector]) sectorData[s.sector] = 0;
                sectorData[s.sector] += s.weight;
            });
            const sectorColors = ['#ff6384','#36a2eb','#ffce56','#4bc0c0','#9966ff','#ff9f40','#00ff88'];
            const ctx = document.getElementById('riskPieChart').getContext('2d');
            new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: Object.keys(sectorData),
                    datasets: [{ data: Object.values(sectorData), backgroundColor: sectorColors.slice(0, Object.keys(sectorData).length), borderColor: '#1a1a2e', borderWidth: 2 }]
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'right', labels: { color: '#888', font: { size: 11 }, padding: 10 } },
                        tooltip: { callbacks: { label: ctx => ctx.label + ': ' + ctx.parsed.toFixed(1) + '%' } }
                    }
                }
            });

            const riskBody = document.getElementById('riskBody');
            riskBody.innerHTML = risk.stocks.map(s =>
                `<tr>
                    <td><strong style="color:#00d4ff">${s.ticker}</strong></td>
                    <td>${s.sector}</td>
                    <td>${s.weight.toFixed(1)}%</td>
                    <td>${s.beta !== null ? s.beta.toFixed(2) : '-'}</td>
                    <td>${s.std_dev !== null ? s.std_dev.toFixed(1) + '%' : '-'}</td>
                    <td>${s.vol_contribution.toFixed(2)}%</td>
                </tr>`
            ).join('');
        }

        // ========== KEY INSIGHTS ==========
        function renderInsights() {
            const container = document.getElementById('insightsContainer');
            let insights = [];

            D.holdings.forEach(h => {
                if (h.total_return_with_div > 200) {
                    insights.push({ type:'success', title: h.ticker + ' - Strong Performer',
                        text: `${h.ticker} has delivered ${h.total_return_with_div.toFixed(1)}% total return (USD) with CAGR of ${h.cagr.toFixed(1)}%.${h.dividends_usd > 0 ? ' Dividends contributed $' + fmtM(h.dividends_usd) + '.' : ''}` });
                }
                if (h.total_return_with_div < 0) {
                    insights.push({ type:'danger', title: h.ticker + ' - Negative Return',
                        text: `${h.ticker} is down ${Math.abs(h.total_return_with_div).toFixed(1)}% in USD terms since ${h.investment_date}.` });
                }
                if (h.beta !== null && h.beta > 1.15) {
                    insights.push({ type:'warning', title: h.ticker + ' - High Beta (' + h.beta.toFixed(2) + ')',
                        text: `Higher sensitivity to market movements. Amplifies both gains and losses.` });
                }
                if (h.sharpe !== null && h.sharpe < 0) {
                    insights.push({ type:'danger', title: h.ticker + ' - Negative Risk-Adjusted Return',
                        text: `Sharpe ratio of ${h.sharpe.toFixed(2)}: returns have not compensated for risk taken.` });
                }
                if (h.sharpe !== null && h.sharpe > 2) {
                    insights.push({ type:'success', title: h.ticker + ' - Excellent Risk-Adjusted Return',
                        text: `Sharpe ratio of ${h.sharpe.toFixed(2)}, well above the 1.0 threshold.` });
                }
            });

            D.sector_summary.forEach(s => {
                const weight = (s.total_current_value / D.totals.total_current_value * 100);
                if (weight > 30) {
                    insights.push({ type:'warning', title: 'Sector Concentration: ' + s.sector,
                        text: `${s.sector} represents ${weight.toFixed(1)}% of portfolio (${s.stocks.join(', ')}).` });
                }
            });

            const t = D.totals;
            if (t.portfolio_beta !== null && t.portfolio_beta > 1.05) {
                insights.push({ type:'warning', title: 'Portfolio Tilts Aggressive',
                    text: `Beta of ${t.portfolio_beta.toFixed(2)} indicates above-market risk.` });
            }
            if (t.portfolio_sharpe !== null && t.portfolio_sharpe > 0.5) {
                insights.push({ type:'success', title: 'Positive Risk-Adjusted Returns',
                    text: `Portfolio Sharpe of ${t.portfolio_sharpe.toFixed(2)} with Sortino of ${t.portfolio_sortino ? t.portfolio_sortino.toFixed(2) : 'N/A'}.` });
            }

            if (insights.length === 0) {
                insights.push({ type:'', title:'No specific insights', text:'No notable observations.' });
            }

            container.innerHTML = insights.map(ins =>
                `<div class="insight-item ${ins.type}"><h4>${ins.title}</h4><p>${ins.text}</p></div>`
            ).join('');
        }

        // ========== GOOGLE SHEETS EXPORT ==========
        function exportToSheets() {
            const headers = ['Ticker','Sector','Investment Date','Inv Price USD','Cur Price USD','TVF Share %',
                             'Investment Amount','Current Value','Dividends','Return USD %','CAGR %','Beta','Sharpe','Sortino'];
            let csv = headers.join('\\t') + '\\n';
            D.holdings.forEach(h => {
                csv += [h.ticker, h.sector, h.investment_date, h.inv_price_usd, h.cur_price_usd,
                        h.shareholding_pct, Math.round(h.investment_amount), Math.round(h.current_value),
                        Math.round(h.dividends_usd), h.total_return_with_div, h.cagr,
                        h.beta||'', h.sharpe||'', h.sortino||''].join('\\t') + '\\n';
            });
            const t = D.totals;
            csv += ['TOTAL','','','','','', Math.round(t.total_investment), Math.round(t.total_current_value),
                    Math.round(t.total_dividends), t.total_return_pct,
                    '', t.portfolio_beta||'', t.portfolio_sharpe||'', t.portfolio_sortino||''].join('\\t') + '\\n';

            navigator.clipboard.writeText(csv).then(() => {
                const sheetsUrl = 'https://docs.google.com/spreadsheets/create';
                window.open(sheetsUrl, '_blank');
                alert('Data copied to clipboard!\\n\\nA new Google Sheet will open.\\nPress Ctrl+V (or Cmd+V) in cell A1 to paste.');
            }).catch(() => {
                const blob = new Blob([csv], {type: 'text/tab-separated-values'});
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url; a.download = 'tvf_portfolio.tsv'; a.click();
                URL.revokeObjectURL(url);
                alert('TSV file downloaded. Open it in Google Sheets via File > Import.');
            });
        }

        // ========== CHAT FUNCTIONS ==========
        async function initializeChat() {
            const apiKey = document.getElementById('apiKey').value;
            const baseUrl = getBaseUrl();
            const model = document.getElementById('model').value;
            const systemPrompt = document.getElementById('systemPrompt').value;

            if (!apiKey) {
                addMessage('Please enter your API key.', 'system');
                return;
            }

            try {
                const response = await fetch('/api/initialize', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ apiKey, baseUrl, model, systemPrompt })
                });

                const data = await response.json();
                if (data.success) {
                    addMessage('Chat initialized! Ask about HALKB, TRENJ, TRMET, TRALT, TCELL, THYAO, TTKOM, TURSG, VAKBN, or KRDMD.', 'system');
                    // Auto-switch to chat tab
                    document.querySelector('.tab-btn:nth-child(2)').click();
                } else {
                    addMessage('Error: ' + data.error, 'system');
                }
            } catch (error) {
                addMessage('Error initializing: ' + error.message, 'system');
            }
        }

        async function sendMessage() {
            const input = document.getElementById('userInput');
            const message = input.value.trim();
            if (!message) return;

            addMessage(message, 'user');
            input.value = '';

            document.getElementById('loading').classList.add('active');

            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message })
                });

                const data = await response.json();
                addMessage(data.response, 'assistant');
            } catch (error) {
                addMessage('Error: ' + error.message, 'system');
            } finally {
                document.getElementById('loading').classList.remove('active');
            }
        }

        function addMessage(text, type) {
            const container = document.getElementById('chatMessages');
            const div = document.createElement('div');
            div.className = 'message ' + type;
            div.textContent = text;
            container.appendChild(div);
            container.scrollTop = container.scrollHeight;
        }

        async function loadPortfolio() {
            const grid = document.getElementById('portfolioGrid');
            grid.innerHTML = '<p style="color:#888">Loading...</p>';

            try {
                const response = await fetch('/api/portfolio');
                const data = await response.json();

                grid.innerHTML = '';
                data.stocks.forEach(stock => {
                    const div = document.createElement('div');
                    div.className = 'stock-item';

                    const changeClass = stock.change_percent > 0 ? 'positive' :
                                       stock.change_percent < 0 ? 'negative' : '';
                    const changeSymbol = stock.change_percent > 0 ? '+' : '';
                    const tickerName = stock.ticker.replace('.IS', '');

                    div.innerHTML = `
                        <div class="stock-symbol">${tickerName}</div>
                        <div class="stock-price">${stock.price || 'N/A'} TRY</div>
                        <div class="stock-change ${changeClass}">
                            ${changeSymbol}${stock.change_percent || 'N/A'}%
                        </div>
                    `;
                    grid.appendChild(div);
                });
            } catch (error) {
                grid.innerHTML = '<p style="color:#ff4466">Error loading portfolio</p>';
            }
        }

        // ========== HELPERS ==========
        function fmtB(n) {
            if (Math.abs(n) >= 1e9) return (n/1e9).toFixed(2) + 'B';
            if (Math.abs(n) >= 1e6) return (n/1e6).toFixed(1) + 'M';
            if (Math.abs(n) >= 1e3) return (n/1e3).toFixed(0) + 'K';
            return n.toFixed(0);
        }
        function fmtM(n) {
            if (Math.abs(n) >= 1e9) return (n/1e9).toFixed(2) + 'B';
            if (Math.abs(n) >= 1e6) return (n/1e6).toFixed(1) + 'M';
            if (Math.abs(n) >= 1e3) return (n/1e3).toFixed(0) + 'K';
            return n.toFixed(0);
        }
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    data = get_cached_dashboard_data()
    data_json = json.dumps(data, default=str)
    html = HTML_TEMPLATE.replace('DASHBOARD_DATA_PLACEHOLDER', data_json)
    return render_template_string(html)


@app.route('/api/data')
def api_data():
    data = get_cached_dashboard_data()
    return jsonify(data)


@app.route('/api/refresh')
def api_refresh():
    global _dashboard_data
    _dashboard_data = None
    data = get_cached_dashboard_data()
    return jsonify({"status": "refreshed", "holdings": len(data["holdings"])})


@app.route('/api/initialize', methods=['POST'])
def initialize():
    data = request.json
    session_id = session.get('session_id', os.urandom(16).hex())
    session['session_id'] = session_id

    try:
        api = YahooFinanceAPI()
        llm = FinanceLLM(
            api_key=data['apiKey'],
            base_url=data['baseUrl'],
            model=data['model'],
            system_prompt=data['systemPrompt'],
            available_functions=api.get_available_functions()
        )

        assistants[session_id] = {
            'api': api,
            'llm': llm
        }

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/chat', methods=['POST'])
def chat():
    session_id = session.get('session_id')
    if not session_id or session_id not in assistants:
        return jsonify({'response': 'Please initialize the chat first.'})

    assistant = assistants[session_id]
    message = request.json.get('message', '')

    def executor(func_name, **kwargs):
        return execute_api_call(assistant['api'], func_name, **kwargs)

    response = assistant['llm'].chat(message, executor)
    return jsonify({'response': response})


@app.route('/api/portfolio')
def portfolio():
    api = YahooFinanceAPI()
    summary = api.get_portfolio_summary()
    return jsonify(summary)


@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'

    print("\n" + "="*50)
    print("  Finance LLM Assistant - Web Interface")
    print("="*50)
    print(f"\nStarting server at http://localhost:{port}")
    print("Press Ctrl+C to stop\n")

    app.run(host='0.0.0.0', port=port, debug=debug)

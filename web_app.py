"""
Web Interface for Finance LLM Assistant
A Flask-based web UI with comprehensive TVF Portfolio Dashboard
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

assistants = {}

# Cache dashboard data (loaded once on startup)
_dashboard_data = None

def get_cached_dashboard_data():
    global _dashboard_data
    if _dashboard_data is None:
        _dashboard_data = get_all_dashboard_data()
    return _dashboard_data


DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TVF Portfolio Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3.0.1/dist/chartjs-plugin-annotation.min.js"></script>
    <style>
        :root {
            --bg-primary: #0f1923;
            --bg-secondary: #1a2634;
            --bg-card: #1e2d3d;
            --bg-hover: #253545;
            --accent: #00d4ff;
            --accent2: #00ff88;
            --red: #ff4466;
            --orange: #ffaa33;
            --text: #e0e8f0;
            --text-muted: #8899aa;
            --border: #2a3a4a;
            --radius: 10px;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
            background: var(--bg-primary);
            color: var(--text);
            min-height: 100vh;
            font-size: 14px;
        }
        .dashboard { max-width: 1600px; margin: 0 auto; padding: 16px; }

        /* Header */
        .header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 16px 24px;
            background: var(--bg-secondary);
            border-radius: var(--radius);
            margin-bottom: 16px;
            border: 1px solid var(--border);
        }
        .header-left h1 { font-size: 1.5em; color: var(--accent); }
        .header-left .subtitle { color: var(--text-muted); font-size: 0.85em; margin-top: 2px; }
        .header-right { display: flex; gap: 20px; align-items: center; }
        .header-stat { text-align: center; }
        .header-stat .label { font-size: 0.7em; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; }
        .header-stat .value { font-size: 1.3em; font-weight: 700; color: var(--accent); }
        .header-stat .value.green { color: var(--accent2); }
        .settings-btn {
            background: var(--bg-card);
            border: 1px solid var(--border);
            color: var(--text);
            padding: 8px 14px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.85em;
            transition: background 0.2s;
        }
        .settings-btn:hover { background: var(--bg-hover); }

        /* Settings Panel */
        .settings-panel {
            display: none;
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 20px;
            margin-bottom: 16px;
        }
        .settings-panel.open { display: block; }
        .settings-panel h3 { color: var(--accent); margin-bottom: 12px; font-size: 1em; }
        .settings-grid { display: flex; flex-wrap: wrap; gap: 16px; }
        .setting-group { min-width: 200px; }
        .setting-group label {
            display: flex; align-items: center; gap: 8px; cursor: pointer;
            padding: 4px 0; font-size: 0.85em; color: var(--text-muted);
        }
        .setting-group label:hover { color: var(--text); }
        .setting-group input[type="checkbox"] { accent-color: var(--accent); }

        /* Cards */
        .cards-row {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 12px;
            margin-bottom: 16px;
        }
        .metric-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 16px;
            position: relative;
            transition: transform 0.15s, box-shadow 0.15s;
        }
        .metric-card:hover { transform: translateY(-2px); box-shadow: 0 4px 16px rgba(0,0,0,0.3); }
        .metric-card .card-label {
            font-size: 0.7em; color: var(--text-muted); text-transform: uppercase;
            letter-spacing: 1px; margin-bottom: 6px;
            display: flex; align-items: center; gap: 6px;
        }
        .metric-card .card-value { font-size: 1.6em; font-weight: 700; }
        .metric-card .card-sub { font-size: 0.8em; color: var(--text-muted); margin-top: 4px; }
        .card-value.positive { color: var(--accent2); }
        .card-value.negative { color: var(--red); }
        .card-value.neutral { color: var(--accent); }

        /* Info tooltip */
        .info-icon {
            display: inline-flex; align-items: center; justify-content: center;
            width: 16px; height: 16px; border-radius: 50%;
            background: var(--border); color: var(--text-muted);
            font-size: 10px; cursor: help; font-style: italic; font-weight: bold;
            position: relative;
        }
        .info-icon .tooltip {
            display: none; position: absolute; bottom: 24px; left: 50%;
            transform: translateX(-50%); background: #1a1a2e; border: 1px solid var(--accent);
            border-radius: 8px; padding: 10px 14px; min-width: 260px; max-width: 350px;
            font-size: 11px; color: var(--text); font-style: normal; font-weight: normal;
            z-index: 1000; line-height: 1.5; box-shadow: 0 4px 20px rgba(0,0,0,0.5);
            letter-spacing: normal; text-transform: none;
        }
        .info-icon:hover .tooltip { display: block; }

        /* Section panels */
        .section {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            margin-bottom: 16px;
            overflow: hidden;
        }
        .section-header {
            display: flex; align-items: center; justify-content: space-between;
            padding: 14px 20px; border-bottom: 1px solid var(--border);
        }
        .section-header h2 { font-size: 1em; color: var(--accent); }
        .section-body { padding: 20px; }

        /* Two-column layout */
        .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }

        /* Charts */
        .chart-container { position: relative; width: 100%; height: 350px; }
        .chart-container canvas { width: 100% !important; height: 100% !important; }

        /* Table */
        .data-table { width: 100%; border-collapse: collapse; font-size: 0.82em; }
        .data-table th {
            background: var(--bg-card); color: var(--text-muted); text-align: left;
            padding: 10px 12px; font-weight: 600; text-transform: uppercase; font-size: 0.8em;
            letter-spacing: 0.5px; border-bottom: 2px solid var(--border);
            position: sticky; top: 0; z-index: 10;
        }
        .data-table td {
            padding: 9px 12px; border-bottom: 1px solid var(--border);
            white-space: nowrap;
        }
        .data-table tr:hover td { background: var(--bg-hover); }
        .data-table .total-row td {
            background: var(--bg-card); font-weight: 700; border-top: 2px solid var(--accent);
            color: var(--accent);
        }
        .data-table .positive { color: var(--accent2); }
        .data-table .negative { color: var(--red); }
        .table-scroll { max-height: 500px; overflow: auto; }

        /* Tabs */
        .tab-bar { display: flex; gap: 4px; padding: 0 20px; background: var(--bg-card); }
        .tab-btn {
            padding: 10px 18px; background: none; border: none; border-bottom: 2px solid transparent;
            color: var(--text-muted); cursor: pointer; font-size: 0.85em; transition: all 0.2s;
        }
        .tab-btn.active { color: var(--accent); border-bottom-color: var(--accent); }
        .tab-btn:hover { color: var(--text); }
        .tab-content { display: none; }
        .tab-content.active { display: block; }

        /* Filter bar */
        .filter-bar { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; }
        .filter-btn {
            padding: 6px 14px; border-radius: 20px; font-size: 0.8em;
            border: 1px solid var(--border); background: var(--bg-card);
            color: var(--text-muted); cursor: pointer; transition: all 0.2s;
        }
        .filter-btn.active { background: var(--accent); color: var(--bg-primary); border-color: var(--accent); }
        .filter-btn:hover { border-color: var(--accent); }

        /* Insights */
        .insight-card {
            background: var(--bg-card); border-radius: 8px; padding: 14px;
            margin-bottom: 10px; border-left: 3px solid var(--accent);
        }
        .insight-card.warning { border-left-color: var(--orange); }
        .insight-card.success { border-left-color: var(--accent2); }
        .insight-card.danger { border-left-color: var(--red); }
        .insight-card h4 { font-size: 0.9em; margin-bottom: 6px; }
        .insight-card p { font-size: 0.82em; color: var(--text-muted); line-height: 1.5; }

        /* Chatbot */
        .chat-panel { display: flex; flex-direction: column; height: 500px; }
        .chat-config { padding: 12px 20px; border-bottom: 1px solid var(--border); display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
        .chat-config input, .chat-config select {
            padding: 7px 10px; border-radius: 6px; border: 1px solid var(--border);
            background: var(--bg-card); color: var(--text); font-size: 0.85em;
        }
        .chat-config input:focus, .chat-config select:focus { outline: none; border-color: var(--accent); }
        .chat-messages { flex: 1; padding: 16px; overflow-y: auto; }
        .chat-msg { margin-bottom: 12px; padding: 10px 14px; border-radius: 10px; max-width: 85%; font-size: 0.88em; white-space: pre-wrap; line-height: 1.5; }
        .chat-msg.user { background: var(--accent); color: var(--bg-primary); margin-left: auto; }
        .chat-msg.assistant { background: var(--bg-card); }
        .chat-msg.system { background: var(--bg-hover); color: var(--text-muted); text-align: center; max-width: 100%; font-size: 0.82em; }
        .chat-input-row { padding: 12px 16px; border-top: 1px solid var(--border); display: flex; gap: 8px; }
        .chat-input-row input { flex: 1; padding: 10px; border-radius: 6px; border: 1px solid var(--border); background: var(--bg-card); color: var(--text); }
        .chat-input-row input:focus { outline: none; border-color: var(--accent); }
        .send-btn { padding: 10px 20px; background: var(--accent); color: var(--bg-primary); border: none; border-radius: 6px; cursor: pointer; font-weight: 600; }
        .send-btn:hover { opacity: 0.85; }

        /* Export button */
        .export-btn {
            padding: 8px 16px; background: var(--accent2); color: var(--bg-primary);
            border: none; border-radius: 6px; cursor: pointer; font-size: 0.82em; font-weight: 600;
        }
        .export-btn:hover { opacity: 0.85; }

        /* Responsive */
        @media (max-width: 1000px) {
            .two-col { grid-template-columns: 1fr; }
            .header { flex-direction: column; gap: 12px; text-align: center; }
            .header-right { flex-wrap: wrap; justify-content: center; }
        }
        @media (max-width: 700px) {
            .cards-row { grid-template-columns: repeat(2, 1fr); }
        }

        /* Spinner */
        .spinner { display: inline-block; width: 16px; height: 16px; border: 2px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.6s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
    </style>
</head>
<body>
<div class="dashboard" id="app">

    <!-- HEADER -->
    <div class="header">
        <div class="header-left">
            <h1>TVF Portfolio Dashboard</h1>
            <div class="subtitle">Turkey Wealth Fund - BIST Stock Analysis</div>
        </div>
        <div class="header-right">
            <div class="header-stat">
                <div class="label">XU100 (TRY)</div>
                <div class="value" id="xu100Try">--</div>
            </div>
            <div class="header-stat">
                <div class="label">XU100 (USD)</div>
                <div class="value green" id="xu100Usd">--</div>
            </div>
            <div class="header-stat">
                <div class="label">USD/TRY</div>
                <div class="value" id="usdtry">--</div>
            </div>
            <button class="settings-btn" onclick="toggleSettings()">Settings</button>
        </div>
    </div>

    <!-- SETTINGS PANEL -->
    <div class="settings-panel" id="settingsPanel">
        <h3>Dashboard Settings</h3>
        <div class="settings-grid">
            <div class="setting-group">
                <strong style="font-size:0.85em;color:var(--text)">Metric Cards</strong>
                <label><input type="checkbox" checked onchange="toggleCard('cardReturn')"> Total Return</label>
                <label><input type="checkbox" checked onchange="toggleCard('cardGain')"> Total Gain</label>
                <label><input type="checkbox" checked onchange="toggleCard('cardCAGR')"> Portfolio CAGR</label>
                <label><input type="checkbox" checked onchange="toggleCard('cardBeta')"> Portfolio Beta</label>
                <label><input type="checkbox" checked onchange="toggleCard('cardSharpe')"> Sharpe Ratio</label>
                <label><input type="checkbox" checked onchange="toggleCard('cardSortino')"> Sortino Ratio</label>
                <label><input type="checkbox" checked onchange="toggleCard('cardStdDev')"> Volatility</label>
                <label><input type="checkbox" checked onchange="toggleCard('cardHoldings')"> Holdings Count</label>
            </div>
            <div class="setting-group">
                <strong style="font-size:0.85em;color:var(--text)">Charts</strong>
                <label><input type="checkbox" id="drawdownToggle" checked onchange="toggleDrawdown()"> Show Drawdown Chart</label>
            </div>
        </div>
    </div>

    <!-- METRIC CARDS -->
    <div class="cards-row" id="cardsRow">
        <div class="metric-card" id="cardReturn">
            <div class="card-label">Total Return (USD)
                <span class="info-icon">i<span class="tooltip">Total portfolio return in USD terms including dividends. Calculated as (Current Value + Dividends - Investment Cost) / Investment Cost. Uses TVF's proportional share of each holding.</span></span>
            </div>
            <div class="card-value" id="vReturn">--</div>
            <div class="card-sub" id="vReturnSub">--</div>
        </div>
        <div class="metric-card" id="cardGain">
            <div class="card-label">Total Gain (USD)
                <span class="info-icon">i<span class="tooltip">Absolute dollar gain = Current portfolio value + Dividends received - Total investment cost. Represents the total profit/loss in nominal USD terms.</span></span>
            </div>
            <div class="card-value neutral" id="vGain">--</div>
            <div class="card-sub" id="vGainSub">--</div>
        </div>
        <div class="metric-card" id="cardCAGR">
            <div class="card-label">Wtd Avg CAGR
                <span class="info-icon">i<span class="tooltip">Value-weighted average Compound Annual Growth Rate across holdings. CAGR = (Ending Value / Beginning Value)^(1/Years) - 1. Represents annualized return for each position.</span></span>
            </div>
            <div class="card-value" id="vCAGR">--</div>
        </div>
        <div class="metric-card" id="cardBeta">
            <div class="card-label">Portfolio Beta
                <span class="info-icon">i<span class="tooltip">Value-weighted average beta vs XU100. Beta measures systematic risk relative to the market. Beta > 1 means more volatile than the market; Beta < 1 means less volatile. Calculated using daily USD returns regression against XU100 index.</span></span>
            </div>
            <div class="card-value neutral" id="vBeta">--</div>
            <div class="card-sub">vs XU100</div>
        </div>
        <div class="metric-card" id="cardSharpe">
            <div class="card-label">Sharpe Ratio
                <span class="info-icon">i<span class="tooltip">Value-weighted average Sharpe Ratio. Measures risk-adjusted return: (Return - Risk-Free Rate) / Standard Deviation. Higher is better. >1 = good, >2 = very good, >3 = excellent. Uses annualized daily USD returns.</span></span>
            </div>
            <div class="card-value" id="vSharpe">--</div>
            <div class="card-sub">risk-adjusted return</div>
        </div>
        <div class="metric-card" id="cardSortino">
            <div class="card-label">Sortino Ratio
                <span class="info-icon">i<span class="tooltip">Value-weighted average Sortino Ratio. Similar to Sharpe but only penalizes downside volatility: (Return - Risk-Free Rate) / Downside Deviation. Better for asymmetric return distributions. Higher Sortino vs Sharpe indicates positively skewed returns.</span></span>
            </div>
            <div class="card-value" id="vSortino">--</div>
            <div class="card-sub">downside risk-adjusted</div>
        </div>
        <div class="metric-card" id="cardStdDev">
            <div class="card-label">Volatility (Ann.)
                <span class="info-icon">i<span class="tooltip">Value-weighted average annualized standard deviation of daily USD returns. Measures total risk (both upside and downside). Calculated as daily std dev x sqrt(252). Higher volatility = wider distribution of potential outcomes.</span></span>
            </div>
            <div class="card-value neutral" id="vStdDev">--</div>
        </div>
        <div class="metric-card" id="cardHoldings">
            <div class="card-label">Holdings</div>
            <div class="card-value neutral" id="vHoldings">--</div>
            <div class="card-sub" id="vSectors">--</div>
        </div>
    </div>

    <!-- INDEXED PERFORMANCE & DRAWDOWN -->
    <div class="two-col">
        <div class="section">
            <div class="section-header">
                <h2>Indexed Performance (Base 100, USD)</h2>
            </div>
            <div class="section-body">
                <div class="chart-container"><canvas id="indexedChart"></canvas></div>
            </div>
        </div>
        <div class="section" id="drawdownSection">
            <div class="section-header">
                <h2>Drawdown from Peak (USD)</h2>
            </div>
            <div class="section-body">
                <div class="chart-container"><canvas id="drawdownChart"></canvas></div>
            </div>
        </div>
    </div>

    <!-- HOLDINGS TABLE -->
    <div class="section">
        <div class="section-header">
            <h2>Holdings</h2>
            <div style="display:flex;gap:8px">
                <button class="export-btn" onclick="exportToSheets()">Export to Google Sheets</button>
            </div>
        </div>
        <div class="section-body" style="padding:0">
            <div class="table-scroll">
                <table class="data-table" id="holdingsTable">
                    <thead>
                        <tr>
                            <th>Ticker</th>
                            <th>Sector</th>
                            <th>Inv. Date</th>
                            <th>Inv. Price (USD)</th>
                            <th>Cur. Price (USD)</th>
                            <th>TVF Share %</th>
                            <th>Inv. Amount ($)</th>
                            <th>Current Value ($)</th>
                            <th>Dividends ($)</th>
                            <th>Return (USD)</th>
                            <th>CAGR</th>
                            <th>Beta</th>
                            <th>Sharpe</th>
                            <th>Sortino</th>
                        </tr>
                    </thead>
                    <tbody id="holdingsBody"></tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- RISK DECOMPOSITION & KEY INSIGHTS -->
    <div class="two-col">
        <div class="section">
            <div class="section-header">
                <h2>Risk Decomposition</h2>
                <span class="info-icon" style="font-size:12px">i
                    <span class="tooltip" style="min-width:300px">Risk decomposition shows how each holding and sector contributes to overall portfolio risk. <br><br><b>Weight:</b> Current market value as % of total portfolio.<br><b>Beta:</b> Sensitivity to market (XU100) movements.<br><b>Std Dev:</b> Annualized volatility of individual holding.<br><b>Vol Contribution:</b> Approximate marginal contribution to portfolio volatility = Weight x StdDev. Does not account for correlations between holdings (which would reduce total portfolio risk via diversification).</span>
                </span>
            </div>
            <div class="section-body">
                <div style="margin-bottom:16px">
                    <div class="chart-container" style="height:250px"><canvas id="riskPieChart"></canvas></div>
                </div>
                <div class="table-scroll" style="max-height:250px">
                    <table class="data-table" id="riskTable">
                        <thead>
                            <tr><th>Ticker</th><th>Sector</th><th>Weight %</th><th>Beta</th><th>Std Dev %</th><th>Vol Contrib %</th></tr>
                        </thead>
                        <tbody id="riskBody"></tbody>
                    </table>
                </div>
            </div>
        </div>
        <div class="section">
            <div class="section-header">
                <h2>Key Insights</h2>
            </div>
            <div class="section-body">
                <div class="filter-bar" id="insightFilters"></div>
                <div id="insightsContainer"></div>
            </div>
        </div>
    </div>

    <!-- CHATBOT -->
    <div class="section">
        <div class="section-header"><h2>AI Assistant</h2></div>
        <div class="chat-panel">
            <div class="chat-config">
                <input type="password" id="chatApiKey" placeholder="API Key (OpenAI/Groq)" style="width:200px">
                <select id="chatProvider" style="width:140px">
                    <option value="https://api.openai.com/v1">OpenAI</option>
                    <option value="https://api.groq.com/openai/v1">Groq</option>
                    <option value="https://api.together.xyz/v1">Together AI</option>
                    <option value="http://localhost:1234/v1">Local</option>
                </select>
                <input type="text" id="chatModel" value="gpt-4o-mini" placeholder="Model" style="width:150px">
                <button class="send-btn" onclick="initChat()" style="font-size:0.82em">Connect</button>
                <span id="chatStatus" style="font-size:0.8em;color:var(--text-muted)">Not connected</span>
            </div>
            <div class="chat-messages" id="chatMessages">
                <div class="chat-msg system">Enter your API key and click Connect to start chatting about your portfolio.</div>
            </div>
            <div class="chat-input-row">
                <input type="text" id="chatInput" placeholder="Ask about your BIST stocks..." onkeypress="if(event.key==='Enter')sendChat()">
                <button class="send-btn" onclick="sendChat()">Send</button>
            </div>
        </div>
    </div>

</div>

<script>
// ==================== DATA ====================
const D = DASHBOARD_DATA_PLACEHOLDER;

// ==================== INIT ====================
document.addEventListener('DOMContentLoaded', () => {
    renderHeader();
    renderCards();
    renderHoldings();
    renderIndexedChart();
    renderDrawdownChart();
    renderRiskDecomposition();
    renderInsights();
});

// ==================== HEADER ====================
function renderHeader() {
    const xu = D.xu100_usd;
    document.getElementById('xu100Try').textContent = xu.xu100_try.toLocaleString();
    document.getElementById('xu100Usd').textContent = xu.xu100_usd.toLocaleString();
    document.getElementById('usdtry').textContent = xu.usdtry.toFixed(2);
}

// ==================== CARDS ====================
function renderCards() {
    const t = D.totals;
    const retEl = document.getElementById('vReturn');
    retEl.textContent = t.total_return_pct.toFixed(1) + '%';
    retEl.className = 'card-value ' + (t.total_return_pct >= 0 ? 'positive' : 'negative');
    document.getElementById('vReturnSub').textContent = 'Invested $' + fmtB(t.total_investment);

    document.getElementById('vGain').textContent = '$' + fmtB(t.total_gain);
    document.getElementById('vGainSub').textContent = 'Dividends: $' + fmtB(t.total_dividends);

    // Weighted avg CAGR
    let sumCW = 0, sumW = 0;
    D.holdings.forEach(h => { sumCW += h.cagr * h.current_value; sumW += h.current_value; });
    const avgCagr = sumW > 0 ? sumCW / sumW : 0;
    const cagrEl = document.getElementById('vCAGR');
    cagrEl.textContent = avgCagr.toFixed(1) + '%';
    cagrEl.className = 'card-value ' + (avgCagr >= 0 ? 'positive' : 'negative');

    const betaEl = document.getElementById('vBeta');
    betaEl.textContent = t.portfolio_beta !== null ? t.portfolio_beta.toFixed(2) : 'N/A';

    const sharpeEl = document.getElementById('vSharpe');
    if (t.portfolio_sharpe !== null) {
        sharpeEl.textContent = t.portfolio_sharpe.toFixed(2);
        sharpeEl.className = 'card-value ' + (t.portfolio_sharpe >= 1 ? 'positive' : t.portfolio_sharpe >= 0 ? 'neutral' : 'negative');
    }

    const sortinoEl = document.getElementById('vSortino');
    if (t.portfolio_sortino !== null) {
        sortinoEl.textContent = t.portfolio_sortino.toFixed(2);
        sortinoEl.className = 'card-value ' + (t.portfolio_sortino >= 1 ? 'positive' : t.portfolio_sortino >= 0 ? 'neutral' : 'negative');
    }

    document.getElementById('vStdDev').textContent = t.portfolio_std !== null ? t.portfolio_std.toFixed(1) + '%' : 'N/A';
    document.getElementById('vHoldings').textContent = t.num_holdings;

    const sectors = [...new Set(D.holdings.map(h => h.sector))];
    document.getElementById('vSectors').textContent = sectors.length + ' sectors';
}

// ==================== HOLDINGS TABLE ====================
function renderHoldings() {
    const body = document.getElementById('holdingsBody');
    let html = '';
    D.holdings.forEach(h => {
        html += `<tr>
            <td><strong style="color:var(--accent)">${h.ticker}</strong></td>
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
    const totalRetPct = t.total_return_pct;
    // Weighted avg metrics for totals row
    let wBeta=0,wSharpe=0,wSortino=0,wCagr=0,wSum=0;
    D.holdings.forEach(h => {
        const w = h.current_value;
        wSum += w;
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
        <td class="${totalRetPct >= 0 ? 'positive' : 'negative'}">${totalRetPct.toFixed(1)}%</td>
        <td class="${(wCagr/wSum) >= 0 ? 'positive' : 'negative'}">${(wCagr/wSum).toFixed(1)}%</td>
        <td>${(wBeta/wSum).toFixed(2)}</td>
        <td>${(wSharpe/wSum).toFixed(2)}</td>
        <td>${(wSortino/wSum).toFixed(2)}</td>
    </tr>`;
    body.innerHTML = html;
}

// ==================== INDEXED PERFORMANCE ====================
let indexedChartInstance = null;
function renderIndexedChart() {
    const ctx = document.getElementById('indexedChart').getContext('2d');
    const perf = D.indexed_performance;
    const colors = {
        THYAO:'#ff6384', TCELL:'#36a2eb', HALKB:'#ffce56', VAKBN:'#4bc0c0',
        TTKOM:'#9966ff', TURSG:'#ff9f40', KRDMD:'#c9cbcf', TRALT:'#00ff88',
        TRMET:'#ff4466', TRENJ:'#00d4ff', XU100:'#ffffff', XU30:'#888888', XBANK:'#aaaaaa'
    };

    // Separate THYAO (uses right Y axis) from others
    const datasets = [];
    const stocksToPlot = ['THYAO','TCELL','HALKB','VAKBN','TTKOM','TURSG','KRDMD','TRALT','TRMET','TRENJ','XU100'];

    stocksToPlot.forEach(comp => {
        if (!perf[comp]) return;
        const d = perf[comp];
        const points = d.dates.map((dt, i) => ({x: dt, y: d.indexed[i]})).filter(p => p.x && p.y !== null);

        datasets.push({
            label: comp,
            data: points,
            borderColor: colors[comp] || '#888',
            borderWidth: comp === 'THYAO' ? 2.5 : 1.5,
            pointRadius: 0,
            tension: 0.1,
            yAxisID: comp === 'THYAO' ? 'y1' : 'y',
            borderDash: comp === 'XU100' ? [5, 3] : [],
        });
    });

    indexedChartInstance = new Chart(ctx, {
        type: 'line',
        data: { datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { position: 'top', labels: { color: '#8899aa', font: { size: 10 }, boxWidth: 12 } },
                tooltip: { backgroundColor: '#1a2634', titleColor: '#00d4ff', bodyColor: '#e0e8f0', borderColor: '#2a3a4a', borderWidth: 1 }
            },
            scales: {
                x: { type: 'category', ticks: { color: '#667788', maxTicksLimit: 10, font:{size:10} }, grid: { color: 'rgba(42,58,74,0.3)' } },
                y: {
                    position: 'left',
                    title: { display: true, text: 'Others (Base 100)', color: '#8899aa' },
                    ticks: { color: '#667788', font:{size:10} },
                    grid: { color: 'rgba(42,58,74,0.3)' },
                    min: 0, max: 350,
                },
                y1: {
                    position: 'right',
                    title: { display: true, text: 'THYAO (Base 100)', color: '#ff6384' },
                    ticks: { color: '#ff6384', font:{size:10} },
                    grid: { drawOnChartArea: false },
                    min: 0, max: 700,
                }
            }
        }
    });
}

// ==================== DRAWDOWN ====================
let drawdownChartInstance = null;
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
            data: points,
            borderColor: colors[comp] || '#888',
            borderWidth: 1.2,
            pointRadius: 0,
            tension: 0.1,
            fill: false,
        });
    });

    drawdownChartInstance = new Chart(ctx, {
        type: 'line',
        data: { datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { position: 'top', labels: { color: '#8899aa', font: { size: 10 }, boxWidth: 12 } },
                tooltip: { backgroundColor: '#1a2634', titleColor: '#00d4ff', bodyColor: '#e0e8f0' }
            },
            scales: {
                x: { type: 'category', ticks: { color: '#667788', maxTicksLimit: 10, font:{size:10} }, grid: { color: 'rgba(42,58,74,0.3)' } },
                y: { ticks: { color: '#667788', callback: v => v+'%', font:{size:10} }, grid: { color: 'rgba(42,58,74,0.3)' } }
            }
        }
    });
}

// ==================== RISK DECOMPOSITION ====================
function renderRiskDecomposition() {
    const risk = D.risk_decomposition;
    // Pie chart by sector
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
            datasets: [{ data: Object.values(sectorData), backgroundColor: sectorColors.slice(0, Object.keys(sectorData).length), borderColor: 'var(--bg-secondary)', borderWidth: 2 }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: {
                legend: { position: 'right', labels: { color: '#8899aa', font: { size: 11 }, padding: 12 } },
                tooltip: { callbacks: { label: ctx => ctx.label + ': ' + ctx.parsed.toFixed(1) + '%' } }
            }
        }
    });

    // Table
    const riskBody = document.getElementById('riskBody');
    let html = '';
    risk.stocks.forEach(s => {
        html += `<tr>
            <td><strong style="color:var(--accent)">${s.ticker}</strong></td>
            <td>${s.sector}</td>
            <td>${s.weight.toFixed(1)}%</td>
            <td>${s.beta !== null ? s.beta.toFixed(2) : '-'}</td>
            <td>${s.std_dev !== null ? s.std_dev.toFixed(1) + '%' : '-'}</td>
            <td>${s.vol_contribution.toFixed(2)}%</td>
        </tr>`;
    });
    riskBody.innerHTML = html;
}

// ==================== KEY INSIGHTS ====================
function renderInsights() {
    const filters = document.getElementById('insightFilters');
    const container = document.getElementById('insightsContainer');

    // Build filter buttons: All, by sector, by company
    const sectors = [...new Set(D.holdings.map(h => h.sector))];
    let filterHtml = '<button class="filter-btn active" onclick="filterInsights(\'all\',this)">All</button>';
    sectors.forEach(s => { filterHtml += `<button class="filter-btn" onclick="filterInsights('sector:${s}',this)">${s}</button>`; });
    D.holdings.forEach(h => { filterHtml += `<button class="filter-btn" onclick="filterInsights('stock:${h.ticker}',this)">${h.ticker}</button>`; });
    filters.innerHTML = filterHtml;

    generateInsights('all');
}

function filterInsights(filter, btn) {
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    generateInsights(filter);
}

function generateInsights(filter) {
    const container = document.getElementById('insightsContainer');
    let insights = [];

    const holdings = filter === 'all' ? D.holdings :
        filter.startsWith('sector:') ? D.holdings.filter(h => h.sector === filter.split(':')[1]) :
        filter.startsWith('stock:') ? D.holdings.filter(h => h.ticker === filter.split(':')[1]) :
        D.holdings;

    // Generate insights based on filtered holdings
    holdings.forEach(h => {
        // Top performers
        if (h.total_return_with_div > 200) {
            insights.push({ type: 'success', title: h.ticker + ' - Strong Performer',
                text: `${h.ticker} has delivered ${h.total_return_with_div.toFixed(1)}% total return (USD) with a CAGR of ${h.cagr.toFixed(1)}%. ${h.dividends_usd > 0 ? 'Dividends contributed $' + fmtM(h.dividends_usd) + '.' : ''}`,
                ticker: h.ticker, sector: h.sector });
        }
        // Underperformers
        if (h.total_return_with_div < 0) {
            insights.push({ type: 'danger', title: h.ticker + ' - Negative Return',
                text: `${h.ticker} is down ${Math.abs(h.total_return_with_div).toFixed(1)}% in USD terms since investment on ${h.investment_date}. Consider reviewing the investment thesis.`,
                ticker: h.ticker, sector: h.sector });
        }
        // High beta warning
        if (h.beta !== null && h.beta > 1.15) {
            insights.push({ type: 'warning', title: h.ticker + ' - High Beta (' + h.beta.toFixed(2) + ')',
                text: `${h.ticker} has a beta of ${h.beta.toFixed(2)}, indicating higher sensitivity to market movements. This position amplifies both gains and losses relative to XU100.`,
                ticker: h.ticker, sector: h.sector });
        }
        // Negative Sharpe
        if (h.sharpe !== null && h.sharpe < 0) {
            insights.push({ type: 'danger', title: h.ticker + ' - Negative Risk-Adjusted Return',
                text: `${h.ticker} has a Sharpe ratio of ${h.sharpe.toFixed(2)}, indicating returns have not compensated for the risk taken. The 1Y USD return is ${h.return_1y !== null ? h.return_1y.toFixed(1) + '%' : 'N/A'}.`,
                ticker: h.ticker, sector: h.sector });
        }
        // Excellent Sharpe
        if (h.sharpe !== null && h.sharpe > 2) {
            insights.push({ type: 'success', title: h.ticker + ' - Excellent Risk-Adjusted Return',
                text: `${h.ticker} has a Sharpe ratio of ${h.sharpe.toFixed(2)}, well above the 1.0 threshold. Strong risk-adjusted performance.`,
                ticker: h.ticker, sector: h.sector });
        }
    });

    // Sector-level insights
    if (filter === 'all' || filter.startsWith('sector:')) {
        D.sector_summary.forEach(s => {
            if (filter.startsWith('sector:') && s.sector !== filter.split(':')[1]) return;
            const weight = (s.total_current_value / D.totals.total_current_value * 100);
            if (weight > 30) {
                insights.push({ type: 'warning', title: 'Sector Concentration: ' + s.sector,
                    text: `${s.sector} represents ${weight.toFixed(1)}% of portfolio value (${s.stocks.join(', ')}). Consider diversification to reduce sector-specific risk.`,
                    sector: s.sector });
            }
        });
    }

    // Portfolio level
    if (filter === 'all') {
        const t = D.totals;
        if (t.portfolio_beta !== null && t.portfolio_beta > 1.05) {
            insights.push({ type: 'warning', title: 'Portfolio Tilts Aggressive',
                text: `Portfolio beta of ${t.portfolio_beta.toFixed(2)} indicates above-market risk. In a downturn, the portfolio is expected to decline more than XU100.` });
        }
        if (t.portfolio_sharpe !== null && t.portfolio_sharpe > 0.5) {
            insights.push({ type: 'success', title: 'Positive Risk-Adjusted Returns',
                text: `Portfolio Sharpe ratio of ${t.portfolio_sharpe.toFixed(2)} suggests adequate compensation for risk taken. Sortino of ${t.portfolio_sortino ? t.portfolio_sortino.toFixed(2) : 'N/A'} indicates limited downside deviation.` });
        }
    }

    if (insights.length === 0) {
        insights.push({ type: '', title: 'No specific insights', text: 'No notable observations for the current filter selection.' });
    }

    container.innerHTML = insights.map(ins =>
        `<div class="insight-card ${ins.type}"><h4>${ins.title}</h4><p>${ins.text}</p></div>`
    ).join('');
}

// ==================== SETTINGS ====================
function toggleSettings() {
    document.getElementById('settingsPanel').classList.toggle('open');
}
function toggleCard(id) {
    const el = document.getElementById(id);
    el.style.display = el.style.display === 'none' ? '' : 'none';
}
function toggleDrawdown() {
    const section = document.getElementById('drawdownSection');
    section.style.display = document.getElementById('drawdownToggle').checked ? '' : 'none';
}

// ==================== CHATBOT ====================
let chatInitialized = false;

async function initChat() {
    const apiKey = document.getElementById('chatApiKey').value;
    const baseUrl = document.getElementById('chatProvider').value;
    const model = document.getElementById('chatModel').value;
    if (!apiKey) { addChatMsg('Please enter your API key.', 'system'); return; }

    document.getElementById('chatStatus').innerHTML = '<span class="spinner"></span> Connecting...';

    const systemPrompt = `You are a helpful financial assistant for Turkish stocks (BIST).
Portfolio tickers: HALKB, TRENJ, TRMET, TRALT, TCELL, THYAO, TTKOM, TURSG, VAKBN, KRDMD
To fetch data, use: {"function": "get_price", "parameters": {"ticker": "THYAO"}}
Available functions: get_stock_info, get_price, get_historical_data, get_portfolio_summary, compare_stocks
Provide clear analysis. This is not financial advice.`;

    try {
        const resp = await fetch('/api/initialize', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({ apiKey: apiKey, baseUrl: baseUrl, model: model, systemPrompt: systemPrompt })
        });
        const data = await resp.json();
        if (data.success) {
            chatInitialized = true;
            document.getElementById('chatStatus').innerHTML = '<span style="color:var(--accent2)">Connected</span>';
            addChatMsg('Chat connected! Ask about HALKB, TRENJ, TRMET, TRALT, TCELL, THYAO, TTKOM, TURSG, VAKBN, or KRDMD.', 'system');
        } else {
            document.getElementById('chatStatus').innerHTML = '<span style="color:var(--red)">Error</span>';
            addChatMsg('Error: ' + data.error, 'system');
        }
    } catch(e) {
        document.getElementById('chatStatus').innerHTML = '<span style="color:var(--red)">Failed</span>';
        addChatMsg('Connection error: ' + e.message, 'system');
    }
}

async function sendChat() {
    const input = document.getElementById('chatInput');
    const msg = input.value.trim();
    if (!msg) return;
    if (!chatInitialized) { addChatMsg('Please connect first by entering your API key and clicking Connect.', 'system'); return; }

    addChatMsg(msg, 'user');
    input.value = '';
    addChatMsg('<span class="spinner"></span> Thinking...', 'system', true);

    try {
        const resp = await fetch('/api/chat', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({ message: msg })
        });
        const data = await resp.json();
        removeLastMsg();
        addChatMsg(data.response, 'assistant');
    } catch(e) {
        removeLastMsg();
        addChatMsg('Error: ' + e.message, 'system');
    }
}

function addChatMsg(text, type, isHtml) {
    const container = document.getElementById('chatMessages');
    const div = document.createElement('div');
    div.className = 'chat-msg ' + type;
    if (isHtml) div.innerHTML = text; else div.textContent = text;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}
function removeLastMsg() {
    const container = document.getElementById('chatMessages');
    if (container.lastChild) container.removeChild(container.lastChild);
}

// ==================== GOOGLE SHEETS EXPORT ====================
function exportToSheets() {
    // Build CSV data for the holdings table
    const headers = ['Ticker','Sector','Investment Date','Inv Price USD','Cur Price USD','TVF Share %',
                     'Investment Amount','Current Value','Dividends','Return USD %','CAGR %','Beta','Sharpe','Sortino'];
    let csv = headers.join('\\t') + '\\n';

    D.holdings.forEach(h => {
        csv += [h.ticker, h.sector, h.investment_date, h.inv_price_usd, h.cur_price_usd,
                h.shareholding_pct, Math.round(h.investment_amount), Math.round(h.current_value),
                Math.round(h.dividends_usd), h.total_return_with_div, h.cagr,
                h.beta||'', h.sharpe||'', h.sortino||''].join('\\t') + '\\n';
    });

    // Total row
    const t = D.totals;
    csv += ['TOTAL','','','','','', Math.round(t.total_investment), Math.round(t.total_current_value),
            Math.round(t.total_dividends), t.total_return_pct,
            '', t.portfolio_beta||'', t.portfolio_sharpe||'', t.portfolio_sortino||''].join('\\t') + '\\n';

    // Copy to clipboard
    navigator.clipboard.writeText(csv).then(() => {
        // Open Google Sheets with paste instructions
        const sheetsUrl = 'https://docs.google.com/spreadsheets/create';
        const win = window.open(sheetsUrl, '_blank');
        alert('Data copied to clipboard!\\n\\nA new Google Sheet will open.\\nPress Ctrl+V (or Cmd+V) in cell A1 to paste the data.');
    }).catch(() => {
        // Fallback: download as TSV file
        const blob = new Blob([csv], {type: 'text/tab-separated-values'});
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'tvf_portfolio.tsv';
        a.click();
        URL.revokeObjectURL(url);
        alert('TSV file downloaded. Open it in Google Sheets via File > Import.');
    });
}

// ==================== HELPERS ====================
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
    # Inject data into HTML
    data_json = json.dumps(data, default=str)
    html = DASHBOARD_HTML.replace('DASHBOARD_DATA_PLACEHOLDER', data_json)
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
        return jsonify({'response': 'Please initialize the chat first by clicking Connect.'})

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
    print("  TVF Portfolio Dashboard")
    print("="*50)
    print(f"\nStarting server at http://localhost:{port}")
    print("Press Ctrl+C to stop\n")

    app.run(host='0.0.0.0', port=port, debug=debug)

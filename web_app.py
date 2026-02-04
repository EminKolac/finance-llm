"""
Web Interface for Finance LLM Assistant
A Flask-based web UI with dynamic configuration for BIST stocks
"""

from flask import Flask, render_template_string, request, jsonify, session
import os
from dotenv import load_dotenv
from yahoo_finance import YahooFinanceAPI, execute_api_call
from llm_interface import FinanceLLM

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

# Store instances per session
assistants = {}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Finance LLM - BIST Stock Assistant</title>
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

        .chat-container {
            flex: 1;
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
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

        @media (max-width: 900px) {
            .grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Finance LLM Assistant</h1>
            <p class="subtitle">BIST Turkish Stock Market Analysis with AI</p>
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
            </main>
        </div>
    </div>

    <script>
        // Toggle custom URL input
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
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


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

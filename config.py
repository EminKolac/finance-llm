"""
Configuration file for Finance LLM Assistant
Edit this file to customize tickers, system prompts, and API settings
"""

# =============================================================================
# YOUR STOCK TICKERS (BIST - Istanbul Stock Exchange)
# =============================================================================
# Format: Just the symbol - the app automatically adds .IS for Yahoo Finance

TICKERS = [
    "HALKB",    # Turkiye Halk Bankasi
    "TRENJ",    # Turk Traktor
    "TRMET",    # Turk Metal
    "TRALT",    # Turk Altin
    "TCELL",    # Turkcell
    "THYAO",    # Turkish Airlines
    "TTKOM",    # Turk Telekom
    "TURSG",    # Turkiye Sigorta
    "VAKBN",    # Turkiye Vakiflar Bankasi
    "KRDMD",    # Kardemir
]

# Yahoo Finance format (with .IS suffix)
YAHOO_TICKERS = [f"{t}.IS" for t in TICKERS]


# =============================================================================
# CUSTOM SYSTEM PROMPTS
# =============================================================================
# Create your own system prompts here
# Use {available_functions} placeholder to include API function documentation

SYSTEM_PROMPTS = {
    "default": """You are a helpful financial assistant for Turkish stocks (BIST).

You can access real-time data for these stocks:
{tickers}

Available functions:
{available_functions}

To call a function, use:
```json
{{"function": "function_name", "parameters": {{"param": "value"}}}}
```

Provide clear, helpful analysis. This is not financial advice.""",

    "turkish": """Sen BIST hisse senetleri konusunda uzmanlasmis bir finansal asistansin.

Su hisselere erisimin var:
{tickers}

Kullanilabilir fonksiyonlar:
{available_functions}

Veri cekmek icin:
```json
{{"function": "fonksiyon_adi", "parameters": {{"parametre": "deger"}}}}
```

Turkce yanit ver. Bu finansal tavsiye degildir.""",

    "technical": """You are a technical analyst specializing in BIST stocks.

Portfolio: {tickers}

Functions: {available_functions}

Call format:
```json
{{"function": "name", "parameters": {{}}}}
```

Focus on:
- Price patterns and trends
- Support/resistance levels
- Moving averages (50/200 day)
- Volume analysis
- RSI and momentum

Provide actionable technical insights. Educational purposes only.""",

    "value_investor": """You are a value investing analyst following Warren Buffett's principles.

Stocks to analyze: {tickers}

Functions: {available_functions}

Data request:
```json
{{"function": "name", "parameters": {{}}}}
```

Focus on:
- P/E ratios and valuation metrics
- Market cap vs intrinsic value
- Dividend yields
- Long-term fundamentals
- Margin of safety

Think long-term. Not financial advice.""",
}


# =============================================================================
# API CONFIGURATION
# =============================================================================
# Supported providers and their base URLs

API_PROVIDERS = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "models": ["llama-3.1-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"]
    },
    "together": {
        "base_url": "https://api.together.xyz/v1",
        "models": ["meta-llama/Llama-3-70b-chat-hf", "mistralai/Mixtral-8x7B-Instruct-v0.1"]
    },
    "local": {
        "base_url": "http://localhost:1234/v1",  # LM Studio, Ollama, etc.
        "models": ["local-model"]
    }
}


# =============================================================================
# HELPER FUNCTION
# =============================================================================

def get_prompt_with_tickers(prompt_name: str) -> str:
    """Get a system prompt with tickers inserted"""
    prompt = SYSTEM_PROMPTS.get(prompt_name, SYSTEM_PROMPTS["default"])
    ticker_list = "\n".join(f"- {t}" for t in TICKERS)
    return prompt.replace("{tickers}", ticker_list)

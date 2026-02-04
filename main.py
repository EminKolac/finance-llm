"""
Finance LLM Assistant - Main Application
A conversational AI assistant for Turkish stock market analysis (BIST)
"""

import os
import json
from dotenv import load_dotenv
from yahoo_finance import YahooFinanceAPI, execute_api_call
from llm_interface import FinanceLLM, LLMConfigManager

# Load environment variables
load_dotenv()


class FinanceAssistant:
    """Main application class for the Finance LLM Assistant"""

    def __init__(self):
        self.api = YahooFinanceAPI()
        self.llm = None
        self.config_manager = LLMConfigManager()
        self._setup_default_configs()

    def _setup_default_configs(self):
        """Setup default system prompt configurations"""

        # Default analyst configuration
        self.config_manager.add_config(
            name="analyst",
            system_prompt="""You are an expert financial analyst specializing in Turkish equities (BIST).

You have access to real-time data for these Turkish stocks:
- HALKB (Turkiye Halk Bankasi) - Banking
- TRENJ (Turk Traktor) - Industrial
- TRMET (Turk Metal) - Mining/Steel
- TRALT (Turk Altin) - Gold/Mining
- TCELL (Turkcell) - Telecommunications
- THYAO (Turkish Airlines) - Aviation
- TTKOM (Turk Telekom) - Telecommunications
- TURSG (Turkiye Sigorta) - Insurance
- VAKBN (Turkiye Vakiflar Bankasi) - Banking
- KRDMD (Kardemir) - Steel/Mining

Available API Functions:
{available_functions}

To fetch data, use this JSON format:
```json
{{"function": "function_name", "parameters": {{"param": "value"}}}}
```

Provide detailed technical analysis when discussing stocks.
Note: This is educational content, not financial advice."""
        )

        # Casual/beginner-friendly configuration
        self.config_manager.add_config(
            name="beginner",
            system_prompt="""You are a friendly financial assistant who explains things in simple terms.

You help users understand Turkish stocks in their portfolio:
- HALKB, VAKBN (Banks)
- TCELL, TTKOM (Telecom)
- THYAO (Turkish Airlines)
- KRDMD, TRMET, TRALT (Mining/Steel)
- TRENJ (Industrial)
- TURSG (Insurance)

Functions you can call:
{available_functions}

Use this format to get data:
```json
{{"function": "function_name", "parameters": {{}}}}
```

Explain everything in simple, easy-to-understand language.
Avoid jargon. This is for educational purposes only."""
        )

        # Turkish language configuration
        self.config_manager.add_config(
            name="turkish",
            system_prompt="""Sen BIST hisse senetleri konusunda uzmanlasmis bir finansal asistansin.

Portfoydeki hisseler:
- HALKB (Turkiye Halk Bankasi)
- TRENJ (Turk Traktor)
- TRMET (Turk Metal)
- TRALT (Turk Altin)
- TCELL (Turkcell)
- THYAO (Turk Hava Yollari)
- TTKOM (Turk Telekom)
- TURSG (Turkiye Sigorta)
- VAKBN (Vakiflar Bankasi)
- KRDMD (Kardemir)

Kullanilabilir fonksiyonlar:
{available_functions}

Veri cekmek icin:
```json
{{"function": "fonksiyon_adi", "parameters": {{"parametre": "deger"}}}}
```

Turkce yanit ver. Bu finansal tavsiye degildir, sadece egitim amaclidir."""
        )

        # Risk-focused configuration
        self.config_manager.add_config(
            name="risk_analyst",
            system_prompt="""You are a risk management specialist analyzing Turkish equities.

Portfolio under analysis:
- HALKB, VAKBN (Banking sector exposure)
- TCELL, TTKOM (Telecom sector)
- THYAO (Aviation - cyclical)
- KRDMD, TRMET (Steel/Commodities)
- TRALT (Gold/Mining)
- TURSG (Insurance)
- TRENJ (Industrial)

API Functions:
{available_functions}

Data request format:
```json
{{"function": "function_name", "parameters": {{}}}}
```

Focus on:
- Volatility analysis
- Sector concentration risks
- Currency exposure (TRY)
- Correlation between holdings

Always highlight potential risks. Not financial advice."""
        )

    def initialize_llm(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        config_name: str = "analyst"
    ):
        """Initialize the LLM with given configuration"""

        config = self.config_manager.get_config(config_name)
        system_prompt = config["system_prompt"] if config else None

        self.llm = FinanceLLM(
            api_key=api_key,
            base_url=base_url,
            model=model,
            system_prompt=system_prompt,
            available_functions=self.api.get_available_functions()
        )

        print(f"[OK] LLM initialized with '{config_name}' configuration")
        print(f"     Model: {model}")
        print(f"     API: {base_url}")

    def change_config(self, config_name: str):
        """Change the system prompt configuration"""
        config = self.config_manager.get_config(config_name)
        if config and self.llm:
            self.llm.update_system_prompt(config["system_prompt"])
            print(f"[OK] Switched to '{config_name}' configuration")
            return True
        elif not config:
            print(f"[ERROR] Configuration '{config_name}' not found")
            print(f"        Available: {self.config_manager.list_configs()}")
            return False
        return False

    def add_custom_config(self, name: str, system_prompt: str):
        """Add a custom system prompt configuration"""
        self.config_manager.add_config(
            name=name,
            system_prompt=system_prompt
        )
        print(f"[OK] Added custom configuration '{name}'")

    def _execute_function(self, function_name: str, **kwargs) -> dict:
        """Execute a Yahoo Finance API function"""
        return execute_api_call(self.api, function_name, **kwargs)

    def chat(self, message: str) -> str:
        """Send a message and get a response"""
        if not self.llm:
            return "Error: LLM not initialized. Call initialize_llm() first."

        return self.llm.chat(message, self._execute_function)

    def interactive_mode(self):
        """Run in interactive mode"""
        print("\n" + "="*60)
        print("    FINANCE LLM ASSISTANT - Turkish Stock Analysis (BIST)")
        print("="*60)
        print("\nCommands:")
        print("  /config <name>  - Change system prompt config")
        print("  /configs        - List available configurations")
        print("  /custom         - Enter custom system prompt")
        print("  /model <name>   - Change model")
        print("  /clear          - Clear conversation history")
        print("  /portfolio      - Show portfolio summary")
        print("  /help           - Show this help")
        print("  /quit           - Exit")
        print("\nYour tickers: HALKB, TRENJ, TRMET, TRALT, TCELL, THYAO,")
        print("              TTKOM, TURSG, VAKBN, KRDMD")
        print("-"*60)

        while True:
            try:
                user_input = input("\nYou: ").strip()

                if not user_input:
                    continue

                # Handle commands
                if user_input.startswith("/"):
                    self._handle_command(user_input)
                    continue

                # Regular chat
                print("\nAssistant: ", end="")
                response = self.chat(user_input)
                print(response)

            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except EOFError:
                break

    def _handle_command(self, command: str):
        """Handle slash commands"""
        parts = command.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else None

        if cmd == "/quit" or cmd == "/exit":
            print("Goodbye!")
            exit(0)

        elif cmd == "/config":
            if arg:
                self.change_config(arg)
            else:
                print("Usage: /config <name>")
                print(f"Available: {self.config_manager.list_configs()}")

        elif cmd == "/configs":
            print("Available configurations:")
            for name in self.config_manager.list_configs():
                print(f"  - {name}")

        elif cmd == "/custom":
            print("Enter your custom system prompt (end with empty line):")
            lines = []
            while True:
                line = input()
                if not line:
                    break
                lines.append(line)
            if lines:
                custom_prompt = "\n".join(lines)
                self.add_custom_config("custom", custom_prompt)
                self.change_config("custom")

        elif cmd == "/model":
            if arg and self.llm:
                self.llm.update_model(arg)
                print(f"[OK] Model changed to: {arg}")
            else:
                print("Usage: /model <model_name>")

        elif cmd == "/clear":
            if self.llm:
                self.llm.clear_history()
                print("[OK] Conversation history cleared")

        elif cmd == "/portfolio":
            print("\nFetching portfolio data...")
            summary = self.api.get_portfolio_summary()
            print("\nPortfolio Summary:")
            print(f"  Total stocks: {summary['total_stocks']}")
            print(f"  Gainers: {summary['gainers']}")
            print(f"  Losers: {summary['losers']}")
            print("\nStocks:")
            for stock in summary['stocks']:
                if 'error' not in stock:
                    change = stock.get('change_percent', 'N/A')
                    ticker_name = stock['ticker'].replace('.IS', '')
                    if change != 'N/A':
                        symbol = "+" if change > 0 else ""
                        print(f"  {ticker_name:8} {stock['price']:>10} {stock['currency']}  ({symbol}{change}%)")
                    else:
                        print(f"  {ticker_name:8} {stock['price']:>10} {stock['currency']}")

        elif cmd == "/help":
            print("\nCommands:")
            print("  /config <name>  - Change system prompt config")
            print("  /configs        - List available configurations")
            print("  /custom         - Enter custom system prompt")
            print("  /model <name>   - Change model")
            print("  /clear          - Clear conversation history")
            print("  /portfolio      - Show portfolio summary")
            print("  /help           - Show this help")
            print("  /quit           - Exit")

        else:
            print(f"Unknown command: {cmd}")
            print("Type /help for available commands")


def main():
    """Main entry point"""
    # Get API key from environment or prompt
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("LLM_MODEL", "gpt-4o-mini")

    if not api_key:
        print("="*60)
        print("  FINANCE LLM ASSISTANT - Setup")
        print("="*60)
        print("\nNo API key found in environment.")
        print("You can set OPENAI_API_KEY in .env file or enter it now.\n")
        api_key = input("Enter your API key: ").strip()

        if not api_key:
            print("Error: API key is required")
            return

    # Initialize assistant
    assistant = FinanceAssistant()
    assistant.initialize_llm(
        api_key=api_key,
        base_url=base_url,
        model=model,
        config_name="analyst"
    )

    # Run interactive mode
    assistant.interactive_mode()


if __name__ == "__main__":
    main()

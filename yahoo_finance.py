"""
Yahoo Finance API Integration Module
Fetches stock data for given tickers using yfinance library
"""

import yfinance as yf
from typing import Optional
from datetime import datetime, timedelta


class YahooFinanceAPI:
    """Wrapper for Yahoo Finance API operations"""

    # Your Turkish stock tickers (BIST)
    DEFAULT_TICKERS = [
        "HALKB.IS",   # Turkiye Halk Bankasi
        "TRENJ.IS",   # Turk Traktor
        "TRMET.IS",   # Turk Metal
        "TRALT.IS",   # Turk Altin
        "TCELL.IS",   # Turkcell
        "THYAO.IS",   # Turkish Airlines
        "TTKOM.IS",   # Turk Telekom
        "TURSG.IS",   # Turkiye Sigorta
        "VAKBN.IS",   # Turkiye Vakiflar Bankasi
        "KRDMD.IS",   # Kardemir
    ]

    @staticmethod
    def convert_ticker(ticker: str) -> str:
        """Convert ticker to Yahoo Finance format (SYMBOL.IS)"""
        # Remove common prefixes
        ticker = ticker.upper().strip()
        if ticker.startswith("IST:"):
            ticker = ticker.replace("IST:", "")
        if ticker.startswith("BIST:"):
            ticker = ticker.replace("BIST:", "")

        # Add .IS suffix if not present
        if not ticker.endswith(".IS"):
            ticker = ticker + ".IS"
        return ticker

    def get_stock_info(self, ticker: str) -> dict:
        """Get comprehensive stock information"""
        ticker = self.convert_ticker(ticker)
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            return {
                "ticker": ticker,
                "name": info.get("longName", info.get("shortName", "N/A")),
                "sector": info.get("sector", "N/A"),
                "industry": info.get("industry", "N/A"),
                "currency": info.get("currency", "TRY"),
                "current_price": info.get("currentPrice", info.get("regularMarketPrice", "N/A")),
                "previous_close": info.get("previousClose", "N/A"),
                "open": info.get("open", info.get("regularMarketOpen", "N/A")),
                "day_high": info.get("dayHigh", info.get("regularMarketDayHigh", "N/A")),
                "day_low": info.get("dayLow", info.get("regularMarketDayLow", "N/A")),
                "volume": info.get("volume", info.get("regularMarketVolume", "N/A")),
                "market_cap": info.get("marketCap", "N/A"),
                "pe_ratio": info.get("trailingPE", "N/A"),
                "dividend_yield": info.get("dividendYield", "N/A"),
                "52_week_high": info.get("fiftyTwoWeekHigh", "N/A"),
                "52_week_low": info.get("fiftyTwoWeekLow", "N/A"),
                "50_day_avg": info.get("fiftyDayAverage", "N/A"),
                "200_day_avg": info.get("twoHundredDayAverage", "N/A"),
            }
        except Exception as e:
            return {"ticker": ticker, "error": str(e)}

    def get_price(self, ticker: str) -> dict:
        """Get current price for a ticker"""
        ticker = self.convert_ticker(ticker)
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            price = info.get("currentPrice", info.get("regularMarketPrice", "N/A"))
            prev_close = info.get("previousClose", 0)
            change = ((price - prev_close) / prev_close * 100) if prev_close and price != "N/A" else "N/A"
            return {
                "ticker": ticker,
                "price": price,
                "currency": info.get("currency", "TRY"),
                "change_percent": round(change, 2) if change != "N/A" else "N/A"
            }
        except Exception as e:
            return {"ticker": ticker, "error": str(e)}

    def get_historical_data(self, ticker: str, period: str = "1mo") -> dict:
        """
        Get historical price data
        period options: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
        """
        ticker = self.convert_ticker(ticker)
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period=period)
            if hist.empty:
                return {"ticker": ticker, "error": "No historical data available"}

            data = []
            for date, row in hist.iterrows():
                data.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "open": round(row["Open"], 2),
                    "high": round(row["High"], 2),
                    "low": round(row["Low"], 2),
                    "close": round(row["Close"], 2),
                    "volume": int(row["Volume"])
                })
            return {
                "ticker": ticker,
                "period": period,
                "data_points": len(data),
                "history": data[-10:] if len(data) > 10 else data  # Return last 10 for brevity
            }
        except Exception as e:
            return {"ticker": ticker, "error": str(e)}

    def get_multiple_prices(self, tickers: Optional[list] = None) -> list:
        """Get prices for multiple tickers"""
        if tickers is None:
            tickers = self.DEFAULT_TICKERS
        return [self.get_price(t) for t in tickers]

    def get_portfolio_summary(self, tickers: Optional[list] = None) -> dict:
        """Get summary for a portfolio of stocks"""
        if tickers is None:
            tickers = self.DEFAULT_TICKERS

        stocks = []
        total_gainers = 0
        total_losers = 0

        for t in tickers:
            data = self.get_price(t)
            stocks.append(data)
            if "error" not in data and data.get("change_percent", 0) != "N/A":
                if data["change_percent"] > 0:
                    total_gainers += 1
                elif data["change_percent"] < 0:
                    total_losers += 1

        return {
            "total_stocks": len(tickers),
            "gainers": total_gainers,
            "losers": total_losers,
            "unchanged": len(tickers) - total_gainers - total_losers,
            "stocks": stocks
        }

    def compare_stocks(self, tickers: list) -> dict:
        """Compare multiple stocks"""
        comparison = []
        for t in tickers:
            info = self.get_stock_info(t)
            comparison.append(info)
        return {"comparison": comparison}

    def get_available_functions(self) -> list:
        """Return list of available API functions for the LLM"""
        return [
            {
                "name": "get_stock_info",
                "description": "Get comprehensive information about a stock including price, volume, PE ratio, market cap, etc.",
                "parameters": {"ticker": "Stock ticker symbol (e.g., 'THYAO' or 'THYAO.IS')"}
            },
            {
                "name": "get_price",
                "description": "Get current price and daily change for a stock",
                "parameters": {"ticker": "Stock ticker symbol"}
            },
            {
                "name": "get_historical_data",
                "description": "Get historical price data for a stock",
                "parameters": {
                    "ticker": "Stock ticker symbol",
                    "period": "Time period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max"
                }
            },
            {
                "name": "get_multiple_prices",
                "description": "Get prices for multiple stocks at once",
                "parameters": {"tickers": "List of ticker symbols (optional, uses default portfolio if not provided)"}
            },
            {
                "name": "get_portfolio_summary",
                "description": "Get summary of portfolio performance",
                "parameters": {"tickers": "List of ticker symbols (optional)"}
            },
            {
                "name": "compare_stocks",
                "description": "Compare multiple stocks side by side",
                "parameters": {"tickers": "List of ticker symbols to compare"}
            }
        ]


# Function to execute API calls based on function name
def execute_api_call(api: YahooFinanceAPI, function_name: str, **kwargs) -> dict:
    """Execute an API function by name with given parameters"""
    functions = {
        "get_stock_info": api.get_stock_info,
        "get_price": api.get_price,
        "get_historical_data": api.get_historical_data,
        "get_multiple_prices": api.get_multiple_prices,
        "get_portfolio_summary": api.get_portfolio_summary,
        "compare_stocks": api.compare_stocks,
    }

    if function_name not in functions:
        return {"error": f"Unknown function: {function_name}"}

    try:
        return functions[function_name](**kwargs)
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    # Test the API
    api = YahooFinanceAPI()
    print("Testing Yahoo Finance API...")
    print("\nDefault tickers:", api.DEFAULT_TICKERS)
    print("\nGetting price for THYAO:")
    print(api.get_price("THYAO"))

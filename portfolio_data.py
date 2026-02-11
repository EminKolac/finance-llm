"""
Portfolio Data Processing Module
Reads TVF Portfolio Excel and computes all metrics for the dashboard
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime


def load_portfolio_data(excel_path="TVF Portfolio V4.xlsx"):
    """Load and process all portfolio data from Excel file"""
    xls = pd.ExcelFile(excel_path)

    overview = pd.read_excel(xls, "Overview")
    dividends = pd.read_excel(xls, "Dividends")
    append1 = pd.read_excel(xls, "Append1")
    usdtry = pd.read_excel(xls, "USDTRY")
    xu100 = pd.read_excel(xls, "XU100")
    xu30 = pd.read_excel(xls, "XU30")
    xbank = pd.read_excel(xls, "XBANK")
    overview_yahoo = pd.read_excel(xls, "Overview_Yahoo")

    data = {
        "overview": overview,
        "dividends": dividends,
        "append1": append1,
        "usdtry": usdtry,
        "xu100": xu100,
        "xu30": xu30,
        "xbank": xbank,
        "overview_yahoo": overview_yahoo,
    }

    # Load individual stock sheets
    stock_sheets = [
        "HALKB", "VAKBN", "TURSG", "TTKOM", "TRMET",
        "TRENJ", "TRALT", "THYAO", "TCELL", "KRDMD"
    ]
    for s in stock_sheets:
        try:
            data[s] = pd.read_excel(xls, s)
        except Exception:
            pass

    return data


def compute_holdings_table(data):
    """Build holdings table with all metrics, properly audited"""
    ov = data["overview"].copy()
    rows = []

    for _, r in ov.iterrows():
        ticker = r["Ticker"].replace("IST:", "")
        inv_usd = r["Investment Price USD"]
        cur_usd = r["Current Price USD"]
        inv_try = r["Investment Price TRY"]
        cur_try = r["Current Price TRY"]
        days = r["Day Elapsed"]
        inv_amt = r["Investment Amount ($)"]
        tvf_share_usd = r["TVF Share ($)"]
        div_usd = r["Dividend (USD)"] if pd.notna(r["Dividend (USD)"]) else 0
        shareholding = r["Shareholding Percentage"]

        # Total return in USD (price-only)
        if inv_usd and inv_usd > 0 and pd.notna(cur_usd):
            total_return_usd = (cur_usd / inv_usd - 1) * 100
        else:
            total_return_usd = 0

        # Total return including dividends (on TVF share basis)
        if inv_amt and inv_amt > 0:
            total_return_with_div = ((tvf_share_usd + div_usd - inv_amt) / inv_amt) * 100
        else:
            total_return_with_div = total_return_usd

        # CAGR in USD
        years = days / 365.25 if days and days > 0 else 1
        if inv_usd and inv_usd > 0 and pd.notna(cur_usd) and years > 0:
            cagr = ((cur_usd / inv_usd) ** (1 / years) - 1) * 100
        else:
            cagr = 0

        row = {
            "ticker": ticker,
            "name": r.get("Name ", ticker),
            "sector": r["Sector"],
            "investment_date": str(r["Investment Date"]),
            "days_elapsed": int(days) if pd.notna(days) else 0,
            "inv_price_try": round(inv_try, 2) if pd.notna(inv_try) else 0,
            "cur_price_try": round(cur_try, 2) if pd.notna(cur_try) else 0,
            "inv_price_usd": round(inv_usd, 4) if pd.notna(inv_usd) else 0,
            "cur_price_usd": round(cur_usd, 4) if pd.notna(cur_usd) else 0,
            "shareholding_pct": round(shareholding * 100, 1) if pd.notna(shareholding) else 0,
            "investment_amount": round(inv_amt, 0) if pd.notna(inv_amt) else 0,
            "current_value": round(tvf_share_usd, 0) if pd.notna(tvf_share_usd) else 0,
            "dividends_usd": round(div_usd, 0),
            "total_return_usd": round(total_return_usd, 2),
            "total_return_with_div": round(total_return_with_div, 2),
            "cagr": round(cagr, 2),
            "eps": round(r["EPS"], 2) if pd.notna(r["EPS"]) else None,
            "high52_try": round(r["High52 (TRY)"], 2) if pd.notna(r["High52 (TRY)"]) else None,
            "low52_try": round(r["Low52 (TRY)"], 2) if pd.notna(r["Low52 (TRY)"]) else None,
            "return_1d": round(r["1D Return USD"] * 100, 2) if pd.notna(r["1D Return USD"]) else None,
            "return_1w": round(r["1W Return USD"] * 100, 2) if pd.notna(r["1W Return USD"]) else None,
            "return_1m": round(r["1M Return"] * 100, 2) if pd.notna(r["1M Return"]) else None,
            "return_1y": round(r["1Y Return USD"] * 100, 2) if pd.notna(r["1Y Return USD"]) else None,
            "ytd_return": round(r["YTD Return"] * 100, 2) if pd.notna(r["YTD Return"]) else None,
            "std_dev": round(r["Standart Sapma"] * 100, 2) if pd.notna(r["Standart Sapma"]) else None,
            "beta": round(r["Beta"], 3) if pd.notna(r["Beta"]) else None,
            "sharpe": round(r["Sharpe"], 3) if pd.notna(r["Sharpe"]) else None,
            "sortino": round(r["Sortino"], 3) if pd.notna(r["Sortino"]) else None,
            "xu100_vol_corr": round(r["XU100 Hacim Korelasyonu"], 3) if pd.notna(r["XU100 Hacim Korelasyonu"]) else None,
        }
        rows.append(row)

    return rows


def compute_portfolio_totals(holdings):
    """Compute portfolio-level totals"""
    total_inv = sum(h["investment_amount"] for h in holdings)
    total_cur = sum(h["current_value"] for h in holdings)
    total_div = sum(h["dividends_usd"] for h in holdings)

    if total_inv > 0:
        total_return = ((total_cur + total_div - total_inv) / total_inv) * 100
    else:
        total_return = 0

    # Weighted average beta (by current value)
    betas = [(h["beta"], h["current_value"]) for h in holdings if h["beta"] is not None]
    if betas:
        portfolio_beta = sum(b * w for b, w in betas) / sum(w for _, w in betas)
    else:
        portfolio_beta = None

    # Weighted average sharpe
    sharpes = [(h["sharpe"], h["current_value"]) for h in holdings if h["sharpe"] is not None]
    if sharpes:
        portfolio_sharpe = sum(s * w for s, w in sharpes) / sum(w for _, w in sharpes)
    else:
        portfolio_sharpe = None

    # Weighted average sortino
    sortinos = [(h["sortino"], h["current_value"]) for h in holdings if h["sortino"] is not None]
    if sortinos:
        portfolio_sortino = sum(s * w for s, w in sortinos) / sum(w for _, w in sortinos)
    else:
        portfolio_sortino = None

    # Weighted std dev
    stds = [(h["std_dev"], h["current_value"]) for h in holdings if h["std_dev"] is not None]
    if stds:
        portfolio_std = sum(s * w for s, w in stds) / sum(w for _, w in stds)
    else:
        portfolio_std = None

    return {
        "total_investment": round(total_inv, 0),
        "total_current_value": round(total_cur, 0),
        "total_dividends": round(total_div, 0),
        "total_gain": round(total_cur + total_div - total_inv, 0),
        "total_return_pct": round(total_return, 2),
        "portfolio_beta": round(portfolio_beta, 3) if portfolio_beta else None,
        "portfolio_sharpe": round(portfolio_sharpe, 3) if portfolio_sharpe else None,
        "portfolio_sortino": round(portfolio_sortino, 3) if portfolio_sortino else None,
        "portfolio_std": round(portfolio_std, 2) if portfolio_std else None,
        "num_holdings": len(holdings),
    }


def compute_indexed_performance(data):
    """Get indexed performance data for charts"""
    app1 = data["append1"]
    result = {}

    stocks = app1["Comp"].unique()
    for comp in stocks:
        df = app1[app1["Comp"] == comp].sort_values("Date").copy()
        if len(df) == 0:
            continue

        dates = []
        for d in df["Date"]:
            if pd.isna(d):
                dates.append(None)
            elif isinstance(d, str):
                dates.append(d)
            elif isinstance(d, (pd.Timestamp, datetime)):
                dates.append(d.strftime("%Y-%m-%d"))
            else:
                dates.append(str(d))

        result[comp] = {
            "dates": dates,
            "indexed": [round(v, 2) if pd.notna(v) else None for v in df["Indexed (Base 100)"].values],
            "cumulative_return": [round(v, 2) if pd.notna(v) else None for v in df["Cumulative Return %"].values],
            "usd_close": [round(v, 4) if pd.notna(v) else None for v in df["USD Close"].values],
        }

    return result


def compute_drawdown(data):
    """Compute drawdown series for each stock"""
    app1 = data["append1"]
    result = {}

    stocks = [c for c in app1["Comp"].unique() if c not in ("XU30", "XBANK", "XU100")]
    for comp in stocks:
        df = app1[app1["Comp"] == comp].sort_values("Date").copy()
        if len(df) == 0:
            continue

        prices = df["USD Close"].values
        dates = []
        for d in df["Date"]:
            if pd.isna(d):
                dates.append(None)
            elif isinstance(d, str):
                dates.append(d)
            elif isinstance(d, (pd.Timestamp, datetime)):
                dates.append(d.strftime("%Y-%m-%d"))
            else:
                dates.append(str(d))

        # Compute drawdown
        peak = prices[0]
        drawdowns = []
        for p in prices:
            if pd.notna(p) and p > peak:
                peak = p
            if pd.notna(p) and peak > 0:
                dd = ((p - peak) / peak) * 100
                drawdowns.append(round(dd, 2))
            else:
                drawdowns.append(0)

        max_dd = min(drawdowns) if drawdowns else 0

        result[comp] = {
            "dates": dates,
            "drawdown": drawdowns,
            "max_drawdown": round(max_dd, 2),
        }

    return result


def compute_xu100_usd(data):
    """Compute XU100 in USD terms"""
    xu100 = data["xu100"].copy()
    usdtry = data["usdtry"].copy()

    # Convert Excel serial dates to datetime for matching
    # XU100 dates are Excel serial numbers with fractional part
    xu100_close = xu100["Close"].values
    usdtry_close = usdtry["Close"].values

    # Simple approach: if lengths align reasonably, use last available
    # Get the latest values
    latest_xu100 = xu100_close[-1] if len(xu100_close) > 0 else 0
    latest_usdtry = usdtry_close[-1] if len(usdtry_close) > 0 else 1

    xu100_usd = latest_xu100 / latest_usdtry if latest_usdtry > 0 else 0

    return {
        "xu100_try": round(float(latest_xu100), 2),
        "usdtry": round(float(latest_usdtry), 4),
        "xu100_usd": round(float(xu100_usd), 2),
    }


def compute_risk_decomposition(holdings):
    """Compute risk contribution by sector and stock"""
    sectors = {}
    total_value = sum(h["current_value"] for h in holdings)

    for h in holdings:
        sector = h["sector"]
        if sector not in sectors:
            sectors[sector] = {
                "sector": sector,
                "stocks": [],
                "total_value": 0,
                "weight": 0,
            }
        sectors[sector]["stocks"].append(h["ticker"])
        sectors[sector]["total_value"] += h["current_value"]

    for s in sectors.values():
        s["weight"] = round((s["total_value"] / total_value) * 100, 2) if total_value > 0 else 0

    # Stock-level weights
    stock_weights = []
    for h in holdings:
        w = (h["current_value"] / total_value * 100) if total_value > 0 else 0
        vol_contribution = w * (h["std_dev"] / 100 if h["std_dev"] else 0) / 100
        stock_weights.append({
            "ticker": h["ticker"],
            "sector": h["sector"],
            "weight": round(w, 2),
            "beta": h["beta"],
            "std_dev": h["std_dev"],
            "vol_contribution": round(vol_contribution * 100, 3),
        })

    return {
        "sectors": list(sectors.values()),
        "stocks": stock_weights,
    }


def compute_sector_summary(holdings):
    """Aggregate returns by sector"""
    sectors = {}
    for h in holdings:
        s = h["sector"]
        if s not in sectors:
            sectors[s] = {"sector": s, "stocks": [], "total_inv": 0, "total_cur": 0, "total_div": 0}
        sectors[s]["stocks"].append(h["ticker"])
        sectors[s]["total_inv"] += h["investment_amount"]
        sectors[s]["total_cur"] += h["current_value"]
        sectors[s]["total_div"] += h["dividends_usd"]

    result = []
    for s in sectors.values():
        if s["total_inv"] > 0:
            ret = ((s["total_cur"] + s["total_div"] - s["total_inv"]) / s["total_inv"]) * 100
        else:
            ret = 0
        result.append({
            "sector": s["sector"],
            "stocks": s["stocks"],
            "total_investment": round(s["total_inv"], 0),
            "total_current_value": round(s["total_cur"], 0),
            "total_dividends": round(s["total_div"], 0),
            "return_pct": round(ret, 2),
        })

    return result


def get_all_dashboard_data(excel_path="TVF Portfolio V4.xlsx"):
    """Main function to get all dashboard data as JSON-serializable dict"""
    data = load_portfolio_data(excel_path)
    holdings = compute_holdings_table(data)
    totals = compute_portfolio_totals(holdings)
    indexed = compute_indexed_performance(data)
    drawdown = compute_drawdown(data)
    xu100_usd = compute_xu100_usd(data)
    risk = compute_risk_decomposition(holdings)
    sectors = compute_sector_summary(holdings)

    return {
        "holdings": holdings,
        "totals": totals,
        "indexed_performance": indexed,
        "drawdown": drawdown,
        "xu100_usd": xu100_usd,
        "risk_decomposition": risk,
        "sector_summary": sectors,
    }


if __name__ == "__main__":
    d = get_all_dashboard_data()
    print(json.dumps(d["totals"], indent=2))
    print("\nHoldings count:", len(d["holdings"]))
    print("Indexed stocks:", list(d["indexed_performance"].keys()))

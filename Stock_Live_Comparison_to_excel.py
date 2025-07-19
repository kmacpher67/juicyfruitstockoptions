from stock_live_comparison import StockLiveComparison

TICKERS = [
    "AMD", "MSFT", "NVDA", "META", "AMZN", "GOOG", "AAPL", "TSLA", "IBM", "ORCL",
    "TEM", "V", "GEV", "CPRX", "CRWD", "CVS", "FMNB", "GD", "JPM", "KMB", "MRVL",
    "NEE", "OKE", "SLB", "STLD", "TMUS",
]

if __name__ == "__main__":
    comp = StockLiveComparison(TICKERS)
    comp.run()

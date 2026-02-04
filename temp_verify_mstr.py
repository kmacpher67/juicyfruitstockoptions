import yfinance as yf
from datetime import datetime

def check_mstr():
    print("Fetching MSTR data...")
    ticker = yf.Ticker("MSTR")
    
    # Check Calendar
    cal = ticker.calendar
    print(f"\nCalendar Type: {type(cal)}")
    print(f"Calendar Content: {cal}")
    
    # Check Info for good measure
    info = ticker.info
    print(f"\nEx-Div Date: {info.get('exDividendDate')}")
    
    # Check if our logic would catch it
    if cal is not None:
        if isinstance(cal, dict) and 'Earnings Date' in cal:
            print("\nFound 'Earnings Date' in dict:")
            for d in cal['Earnings Date']:
                print(f" - {d}")
        elif hasattr(cal, "empty") and not cal.empty:
             print("\nFound DataFrame/Series content (legacy):")
             print(cal)

if __name__ == "__main__":
    check_mstr()

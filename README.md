

Write a program to find call option chains for a given equity stock for example ORCL Oracle Corp find best time value options for an out of the money strike price becareful of yfinance rate limits (limit option chains) for inputs allow an array of stock tickers to be entered default ["ORCL", "AMZN", "XOM"] prompt for a minimum annualized return on investment in percentage of return, Enter minimum option volume (default 20), Enter maximum number of expiration dates to analyze (default 4), filter on Minimum annualized time value: 11%, Maximum OTM percentage (10%),  and rank the juiciest from top to bottom with a maximum of 15 

### ask to fix annualized return 

how did you calculate the annualized return? seems a bit high? for example i see ticker expirationDate strike lastPrice timeValue annualizedReturn percentOTM volume openInterest daysToExpiration 11 ORCL 2025-02-28 170.0 2.52 2.52 5214.29 1.31 376.0 566.0 7 having a return of 77% lastprice = 2.52 / 170 *365/7 *100 = 77.294%


def calculate_metrics(row):
    """
    Calculate time value and annualized return
    Time Value = Option Price - Intrinsic Value
    Annualized Return = (Option Premium / Strike Price) * (365/DTE) * 100
    """
    intrinsic_value = max(0, row['stockPrice'] - row['strike'])
    time_value = row['lastPrice'] - intrinsic_value

    # Calculate annualized return
    if row['daysToExpiration'] > 0:
        # Calculate return as (premium/strike) * (365/DTE) * 100
        annualized_return = (row['lastPrice'] / row['strike']) * (365 / row['daysToExpiration']) * 100
    else:
        annualized_return = 0


The new calculation:

Takes the option premium (lastPrice) divided by the strike price
Multiplies by (365/DaysToExpiration) to annualize
Multiplies by 100 to convert to percentage
This matches your calculation example:

For ORCL with lastPrice = 2.52, strike = 170, and DTE = 7
(2.52 / 170) * (365/7) * 100 ≈ 77.29%
The previous version was incorrectly using the time value and option premium in the denominator, which led to inflated returns. The new version properly calculates the return based on the capital at risk (strike price) and annualizes it based on days to expiration.

Would you like to run this corrected version to see the more accurate return calculations?

## version 3 after fixes 

/tmp/option_analyzer_v3.py




option_analyzer.py

pip install yfinance pandas numpy

Let me explain how this program works:

The program uses yfinance to fetch real-time stock and options data from Yahoo Finance.

Key features:

Finds out-of-the-money (OTM) call options for a given stock
Calculates time value for each option
Computes annualized time value percentage
Filters options by minimum volume to ensure liquidity
Sorts and displays the best opportunities based on time value
For each option, it shows:

Expiration date
Strike price
Last price (premium)
Volume and open interest
Time value
Days to expiry
Annualized time value percentage
Let's run the program with ORCL as an example:

Tool Use: bash
Input: {'command': 'python /tmp/option_analyzer.py'}


Fail 404 error 
Ah, I see the issue. The error occurs because Yahoo Finance's API has some rate limiting and access restrictions. Let me modify the code to use a more reliable method and add better error handling:




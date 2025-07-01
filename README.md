JUICY FRUIT OPTIONS and IBRK optimization code 

Write a program to find call option chains for a given equity stock for example ORCL Oracle Corp find best time value options for an out of the money strike price becareful of yfinance rate limits (limit option chains) for inputs allow an array of stock tickers to be entered default ["ORCL", "AMZN", "XOM"] prompt for a minimum annualized return on investment in percentage of return, Enter minimum option volume (default 20), Enter maximum number of expiration dates to analyze (default 4), filter on Minimum annualized time value: 11%, Maximum OTM percentage (10%),  and rank the juiciest from top to bottom with a maximum of 15 

Chat Ghepetto and it's CODEX is helping me with this repo, let's see how much shitty code i have to debug after this AI "help"

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



## Codebase Overview

The following summary was generated in a previous conversation to help new contributors understand the repository.

**General Structure**

- The repository mostly contains stand-alone Python scripts for analyzing stock option chains.
- Several iterations exist, e.g. `option_analyzer_v2.py` up to `option_analyzer_v5.py`, along with related scripts such as `option_optimizer.py` and `option_time_value_v*.py`.
- The Dockerfile installs dependencies (yfinance, pandas, numpy) and runs `option_analyzer_v5.py` by default.
- Shell scripts (`startclaude.sh`, `shellintodocker.sh`) help build and run the Docker container.
- CSV files (e.g. `recommendations.csv`) capture sample outputs.

**Main Functionality**

- The latest analyzer defines `analyze_option_chain` which fetches option chains via yfinance, filters by parameters like minimum volume, allowable "out-of-the-money" percentage, and computes annualized time value percentages.
- Results are sorted and displayed, and the function can return a dataframe with the best opportunities.
- `option_optimizer.py` extends the analyzer with additional filters such as minimum days to expiration and allows iterating over multiple tickers.
- `portfolio-fixer.py` reads a portfolio CSV, determines covered call positions, and invokes `analyze_option_chain` to suggest rolling or selling options.

**Important Details**

- All scripts rely heavily on the `yfinance` API for fetching market data, with retries implemented in helpers like `get_current_price`.
- Rate limiting is handled with `time.sleep` calls in the option chain fetch functions.
- Output CSVs are saved with timestamps for record keeping.
- The README provides a rough idea of the intended workflow, including how annualized return is computed.

**Next Steps to Learn**

1. **Explore yfinance** – Since all analyses depend on this library, learning its methods for retrieving historical prices and option chains will help adapt or extend the scripts.
2. **Pandas DataFrame operations** – Filtering, merging, and sorting DataFrames is central to how results are computed and displayed.
3. **Options terminology** – Understanding concepts like "out of the money," "time value," and annualized returns is key for interpreting the output.
4. **Docker usage** – The Dockerfile and helper scripts show how to package and run the analyzer in an isolated environment. Familiarity with Docker will help customize or deploy the tool elsewhere.
5. **Potential refactoring** – The code could be organized into a package with shared modules for fetching data and computing metrics; diving deeper into Python packaging and testing would be a natural next step.

Overall, start by running `option_analyzer_v5.py` (or `option_optimizer.py` for multiple tickers) in the provided Docker container, experiment with the filter parameters, and examine the generated CSV outputs to understand how the tool surfaces high time-value call options.

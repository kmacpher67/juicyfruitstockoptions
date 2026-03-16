# Project Context: Juicy Fruit
**Status:** Active Development
**Lead Developer:** Ken MacPherson

## Tech Stack & Environment
- **Platform:** 
    - **Development:** Ubuntu (ThinkPad P53), Windows 11 (former Gaming computer)
    - **Production:** AWS EC2 (Ubuntu*) or Atlantic.net VPS (Ubuntu*)
    - **Containerization:** Docker, docker-compose
- **Primary Languages:** Python, JavaScript (Node.js v20+), Bash
- **Trading Platform:** Interactive Brokers (IBKR) API
- **Model Preference:** Prioritize efficiency and logic for financial calculations.
    - **AI Models:**
        - **OpenAI API:** Monthly Paid Account, no api credits 
        - **Google Gemini API:** Monthly Paid Account, no api credits 
        - **Anthropic API:** Free Account, some api credits
        - **GROK API:** Free Account, no credits 
        - **Python:** FastAPI, Pandas, NumPy, Scikit-learn, TensorFlow, PyTorch, etc.
        - **Local LLM:** Ollama (Llama 3.3, etc.)
        - **Local Vector DB:** ChromaDB
- **Database:** MongoDB, SQL Lite, Maybe PostgreSQL (future)

## Coding Standards
- **Annualized Yield:** Whenever I ask for a 'return' or 'yield' on a trade or position, always calculate both the simple return and the **annualized yield** for reference and comparison.
- **Cost Basis:** Use a reset-cost-basis logic for diagonal moves. For example, if I roll a position and lock in cash, treat the net cash-out as the new basis for the subsequent leg.
- **Error Handling:** Write robust error handling for API calls, specifically looking for "connection reset" or "rate limit" issues common with financial APIs.

## Business Logic
- Call/Put Skew is the ratio of the price of a put option to the price of a call option with the 6% OTM ~1 year out expiration date is the fundemental secret sauce to juicy fruits. Higher CALL premiums divided by PUT premiums shows real bets on the stock going up. Lower CALL premiums divided by PUT premiums shows real bets on the stock going down. 
- This project manages stock options (Covered Calls, Cash Secured Puts to aquire stock or just profits, Calendar Spreads, Diagonals).
- Data source: Local CSVs and IBKR live feed. Save all data to a local CSV file and mongo database collection for historical tracking and web app usage.
- Focus: I manage 3 accounts (two IRA and 1 taxable account). I have multiple positions in each account. I want to be able to see all my positions, results and metrics in one place and be able to see the overall health of my portfolio as well by each account.
## System Notes
- Remember the "Pressure Switch" fix for hardware-related scripts (Inducer port cleaning).
- Default to scannable Markdown tables for financial reports.
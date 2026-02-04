# Agent Frameworks: Building the "Brain"

This document explores how to implement the "Antigravity" Agent capability for the dashboard.

## Option A: General Purpose LLM Frameworks (LangChain / LangGraph)
*   **What**: Orchestration layers that connect an LLM (GPT-4, Claude) to tools (Calculators, API calls, Search).
*   **Use Case**: "Chat with your Portfolio."
    *   *User*: "Analyze my risk on AAPL."
    *   *Agent*: Calls `get_portfolio()`, calls `calculate_greeks()`, interprets results, responds in English.
*   **Pros**: Extremely flexible, rapidly evolving, handles unstructured tasks well.
*   **Cons**: Not reliable for *execution*. You don't want an LLM "hallucinating" a trade order due to a prompt injection.

## Option B: Specialized Trading Bot Libraries (Lumibot)
*   **What**: Python libraries designed specifically for algo-trading.
*   **Structure**: `on_trading_iteration(strategy)`, `on_market_open()`, etc.
*   **Use Case**: The "Hands" and "Eyes" of the system.
    *   *Bot*: Polls data, checks strict logic (If Price < X, Buy), executes order via IBKR API.
*   **Pros**: Reliable, deterministic, built-in backtesting, broker connectors (IBKR, Alpaca).
*   **Cons**: "Dumb". It only does exactly what you code it to do.

## The Hybrid Approach (Recommended)
Use **Lumibot** (or similar) handles the "Body" (Execution, Data feed, Safety checks, Risk limits).
Use **LangChain** handles the "Brain" (Strategy selection, Sentiment analysis, User Interface).

*   **Workflow**:
    1.  **LangChain Agent** analyzes News + Macro + Portfolio -> Decides "Market Condition is Bullish Volatility".
    2.  **LangChain Agent** updates a configuration file or database Application State.
    3.  **Lumibot Strategy** reads the state ("Bullish Vol") and activates the specific sub-strategy logic (e.g., "Sell Puts") coded deterministically in Python.

## Other Contenders
*   **Autogen (Microsoft)**: Good for multi-agent conversation (e.g., "Risk Agent" argues with "Greed Agent" to find a balanced trade).
*   **CrewAI**: Role-based agents (similar to Autogen but higher level).

## Using My Gemini Pro Account
*   **What**: Use my Gemini Pro Account to generate natural language `reasoning`.

To integrate an interactive trading agent into Juicy Fruit Traders, you have two primary paths: a programmatic API integration for your Python/LangGraph stack, or a "quick link" method using Custom Gems for fast scenario testing.

Since you are already using LangGraph and Python, the API route is significantly more powerful for your "Deep Roll" evaluations as it can pull live data from your MongoDB and IBKR feeds.

### 1. Creating the Interactive Trading Agent
The Programmatic Method (Best for "Juicy Fruit")
Since your app already uses LangGraph, you can treat Gemini Pro as a specialized "Analyst Node."

Tool Calling: Use the Gemini API to define tools that fetch your current AMD cost basis and P&L directly from MongoDB.

Prompting Strategy: System prompts should focus on your "Bad Trade Heuristics."

Annualized Yield Requirement: Per your previous instruction, your agent logic should include a function to calculate (Credit/Debit/Strike)×(365/DTE) for every roll recommendation.

### 2. The "Quick Link" Method (Custom Gems)
If you want a faster, UI-based way to test the scenario you provided without coding:

Go to the Gemini web interface and create a Gem named "Juicy Fruit Advisor."

System Instructions: "You are a specialized options trading advisor for an IRA account. Always calculate annualized yield for rolls. Evaluate strategies based on three pillars: Up & Out, Shorter Out (higher strike), and Time-Only Out."

Data Input: Paste your AMD scenario. The Gem will remember your "No Mustard/Ketchup" level of directness and your specific trading rules.

### 3. Google Cloud AI API (Gemini via API Key)

To integrate Gemini Pro programmatically into "Juicy Fruit":

1.  **Get API Key**: [Google AI Studio](https://aistudio.google.com/app/apikey).
2.  **Persist Key**: Add to your `.bashrc` for implicit authentication.
    ```bash
    echo 'export GOOGLE_API_KEY="your_key_here"' >> ~/.bashrc
    source ~/.bashrc
    ```
3.  **Library**: Use `google-generativeai` (Google AI Studio SDK).

**Implementation Details**:
- **Service**: `app/services/llm_service.py` (`GeminiService`) handles the connection.
- **Frontend Access**: A "Trading Agent" link is available in the **Type** column of the Portfolio Grid. Clicking it opens a contextual analysis window.
- **Reasoning**: The system generates prompts using your portfolio context (Ticker, Cost Basis, Risk) and requests "Reasoning" based on "Bad Trade Heuristics".

```python
# Service Example
import google.generativeai as genai
genai.configure(api_key=settings.GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-pro')
response = model.generate_content("Analyze AAPL for covered call...")
print(response.text)
```
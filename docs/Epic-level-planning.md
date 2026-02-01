# Epic-level planning
- This is a TBD project wish list or to-do list for the stock options project.
- Epic is an agile waterfall term for a large project or feature set, so not really a project plan, but a wish list (not as rigorous as a project plan, more of a bookmark, maybe a loose roadmap).
- When an epic item is completed it should be strikethrough and have a checkmark to note completion. 
- From this i would create a google antigravity implementation plan and task list. 
- When performing an implementation plan based on this epic, i would use the following rules:
-- the implementation plan should be broken down into smaller tasks that can be completed in a reasonable amount of time (e.g., 1-2 hours)
-- implementation plan should be created using google antigravity
-- incremental implementation plan should follow hierarchical decomposition for naming based the short name of the epic (e.g., epic-001-algorithmic-trading-001-task-001)
-- each PROPOSED high level implementation plan should noted if it can be run in parallel by multiple agents or people
-- If an agent is asked to review and clean up this EPIC document, it should add a new section called "Review and Cleanup" and note if it can be run in parallel by multiple agents or people
-- a reviewing agent of this Epic document should follow .agent/rules/document.md and .agent/rules/implementation-plan.md
-- each task should have a clear objective and a set of deliverables
-- each task should have a clear owner and a clear timeline
-- each task should have a clear definition of done
-- each task should have a clear definition of done

## algorithmic trading
- analyze existing option positions in portfolio and recommend buy, sell, hold, exercise, or calendar diagonal
- analyze option positions and recommend covered call opportunities 
- analyze option positions and recommend call buy opportunities 
- target certain stocks and their options based on macro trends and news
- build a trading history of Kens previous trades and their performance 
- based on Ken's trading history, build a trading strategy 
- Core playbooks: Momentum, Mean-Reversion, Seasonality
- Metric stack: Sharpe, Sortino, MaxDD, hit-rate, turnover

## Analysis
- find juciy option covered call opportunities or call buy opportunities 
- using juicy calls to fund downward trending stocks vs buying puts
- ML in the Loop (8-step flow)
-- Universe selection
-- Feature engineering (momentum, quality)
-- Time-series CV (no leakage)
-- Model training (XGBoost)
-- Validation (IC, IC-IR, feat importance)
-- Signal creation (scores)
-- Backtest (Zipline/VectorBT)
-- Portfolio analysis

## dashboard features 
- graphs or links to graphs of stock price vs moving averages or local for portfolio private
- yields vs cost basis and returns on investment
- guardrails for losses or out of control algo or ken's bad trades
- Menu item to manage all the automated processes that to kicked off by the scheduler
-- How to pause or stop the scheduler
-- How to resume the scheduler
-- How to view the logs of the scheduler
-- How to view the status of the scheduler
-- How to view the history of the scheduler
-- How to view the settings of the scheduler
- Help hints on how to use or explain the formulas and metrics on the dashboard (hover hints or links to docs) 
-- use existing library to generate the help hints and help system? 
-- Integrate to AI chatbot to answer questions about the dashboard and metrics


## techincial issues cleanup and nfrs
- mcp server md-converter to convert .md files to docx files for memorization
- rules and plans to move to documents to be stored in google docs 
- ability to back play strategies using IBKR data and/or IBKR API 
- do we need to build a tws api (docker) to connect to IBKR?
- local model hosting for AI 
-- where to put this? home PC or cloud? costs vs benefits and headaches
- mongo backup to github is manual and how to automate this? 
-- Is this best location for backup or maybe into google drive? 
--- Have agent follow learning-opportunity.md and recommend best practices for mongo backup and automation given my current setup (docker and local on prem maybe future running in cloud)??
- Run docker containers on home PC vs cloud and costs vs benefits and headaches 
-- hardening and securing docker containers when running connected to the internet
- UI should logout if the authentication token expires (should be synced with backend) 
-- UI settings admin set default and minimum (users can override but not below minimum) 
- RAGS for documentation and help system
- RAGS for trading history and analysis of ken's portfolio and trades
- buy vs build analysis for features Tools and libraries: 


# safety and protection
- Guardrails: position limits, slippage, stop rules

### Agentic AI
- what are the concerns should i be aware of with agentic AI?
- first prototype of agentic AI to use langchain and openai to create a chatbot that can answer questions about the stock market
- Scikit-learn (ML) when how to use it in this project or offer ideas for me? 
- Track & compare ideas: MLflow (free) when, how, best practices for this project?
- 

# Changelog 
-- Date         Action    Reason
-- 2026-02-01   DELETED   initial draft completed before ai agent clean up
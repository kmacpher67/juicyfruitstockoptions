# Epic-level planning
This is a TBD project wish list or to-do list for the stock options project.
Epic is an agile waterfall term for a large project or feature set, so not really a project plan, but a wish list (not as rigorous as a project plan, more of a bookmark, maybe a loose roadmap).
From this i would create a google antigravity implementation plan and task list. 

## algorithmic trading
- analyze existing option positions in portfolio and recommend buy, sell, hold, exercise, or calendar diagonal
- analyze option positions and recommend covered call opportunities 
- analyze option positions and recommend call buy opportunities 
- target certain stocks and their options based on macro trends and news
- build a trading history of Kens previous trades and their performance 
- based on Ken's trading history, build a trading strategy 

## Stock Analysis
- find juciy option covered call opportunities or call buy opportunities 
- using juicy calls to fund downward trending stocks vs buying puts

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


## techincial issues cleanup 
- mcp server md-converter to convert .md files to docx files for memorization
- rules and plans to move to documents to be stored in google docs 
- ability to back play strategies using IBKR data and/or IBKR API 
- do we need to build a tws api (docker) to connect to IBKR?
- local model hosting for AI 
-- where to put this? home PC or cloud? costs vs benefits and headaches

### Agentic AI
- what are the concerns should i be aware of with agentic AI?
- first prototype of agentic AI to use langchain and openai to create a chatbot that can answer questions about the stock market
- 

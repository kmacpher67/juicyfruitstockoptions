# Task Checklist - Agent Frameworks & LLM Features

- [/] **Dependencies & Config**
    - [x] Add `google-generativeai` & `python-dotenv` to `requirements.txt`
    - [x] Update `app/config.py` with `GOOGLE_API_KEY` and `GEMINI_MODEL`

- [x] **Backend Service**
    - [x] Create `app/services/llm_service.py` (GeminiService)
    - [x] Implement `generate_reasoning`
    - [x] Implement `get_trade_analysis`
    - [x] Create `tests/test_llm_service.py` and pass tests

- [x] **Frontend Integration**
    - [x] Update `PortfolioGrid.jsx` to add "Trading Agent" link in Type column
    - [x] Ensure link filters by Account and Ticker/Type correctly

- [x] **Documentation**
    - [x] Update `docs/learning/agent-frameworks.md` with Gemini details
    - [x] Update `docs/features-requirements.md` (check off items)

- [x] **Verification**
    - [x] Run backend tests
    - [x] Manual verification (check link generation)

# Implementation Plan - Agent Frameworks & Gemini Integration (Future LLM)

This plan addresses the "Future LLM" and "Trading Agent" requirements by establishing the foundation for Agentic AI using Google's Gemini Pro model. It focuses on infrastructure, service creation, and documentation updates.

## User Review Required
> [!IMPORTANT]
> **API Key Required**: This implementation requires a valid `GOOGLE_API_KEY` for accessing Gemini models. You will need to add this to your `.env` file.

### How to get a Google API Key & Persist it
1.  Go to [Google AI Studio](https://aistudio.google.com/app/apikey).
2.  Click **Create API key**.
3.  Select a project or create a new one.
4.  **Option A: Project-Level (.env)**
    Copy the generated key and paste it into your `.env` file:
    ```bash
    GOOGLE_API_KEY=your_key_here_...
    ```
5.  **Option B: System-Level (Persistent)**
    To make the key available in every terminal session automatically:
    ```bash
    echo 'export GOOGLE_API_KEY="your_key_here_..."' >> ~/.bashrc
    source ~/.bashrc
    ```

### SDK Note
We will use the **`google-generativeai`** library (AI Studio SDK), which is the standard Python client for using the API Key method. 
*Note: The user-referenced `google-cloud-aiplatform` is for Vertex AI (GCP), which requires more complex IAM service account authentication. For the "Juicy Fruit" project, the AI Studio API Key approach is simpler and sufficient.*

## Proposed Changes

### Configuration & Dependencies
#### [MODIFY] [requirements.txt](file:///home/kenmac/personal/juicyfruitstockoptions/requirements.txt)
- Add `google-generativeai`.
- Add `python-dotenv`.

#### [MODIFY] [app/config.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/config.py)
- Add `GOOGLE_API_KEY` to `Settings` class.
- Add `GEMINI_MODEL` (default: "gemini-pro").

### Services
#### [NEW] [app/services/llm_service.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/services/llm_service.py)
- Create `GeminiService` class.
- Implement `generate_reasoning(context: str) -> str`: Generic reasoning hook.
- Implement `get_trade_analysis(ticker: str, ecosystem_context: dict) -> str`: Specific method for trading advice prompt construction.

### Frontend
#### [MODIFY] [app/ui/components/PortfolioGrid.jsx](file:///home/kenmac/personal/juicyfruitstockoptions/app/ui/components/PortfolioGrid.jsx)
- **Grid Update**: In the "Type" column renderer, add a clickable link/icon.
- **Link Logic**:
    - If Type is STK: Link searches for all options (OPT) related to this stock for just the account.
    - If Type is OPT: Link searches for the underlying stock (STK) and other options for just the account.
    - **Action**: Opens a new browser tab/window pointing to the Trading Agent Interface (e.g., `/agent/analysis?ticker=MX&context=...`).
    - *Note: For this iteration, we will implement the link to opening a placeholder Agent page with the query parameters populated.*

### Documentation
#### [MODIFY] [docs/learning/agent-frameworks.md](file:///home/kenmac/personal/juicyfruitstockoptions/docs/learning/agent-frameworks.md)
- Refine "Using My Gemini Pro Account" section to align with the new `GeminiService`.
- Expand on "The Programmatic Method" with specific prompt templates and architecture diagrams.
- Ensure the "Quick Link" method is preserved as an alternative.

#### [MODIFY] [docs/features-requirements.md](file:///home/kenmac/personal/juicyfruitstockoptions/docs/features-requirements.md)
- Update "Agentic AI & Intelligence" section.
- Cross-reference new dependency.
- Add detailed Todo items for "Context Assembly" and "Prompt Templates".

## Verification Plan

### Automated Tests
- **Unit Tests**: Create `tests/test_llm_service.py`.
    - Mock `google.generativeai.GenerativeModel`.
    - Verify `generate_reasoning` handles API responses correctly.
    - Verify `get_trade_analysis` constructs prompts with provided context (Ticker, Risk, Cost Basis).
    - Verify `get_trade_analysis` constructs prompts with provided context (Ticker, Risk, Cost Basis).
    - command: `pytest tests/test_llm_service.py`

- **Frontend Tests**: 
    - Verify that the "Type" column link is rendered correctly for STK and OPT rows.
    - Verify the constructed URL contains the correct query parameters (ticker, context).

### Manual Verification
1.  **Environment Setup**: Add dummy `GOOGLE_API_KEY` to `.env` (or real one if available).
2.  **Service Check**: Use a script to instantiate `GeminiService` and call `generate_reasoning` (will fail without real key, but verifies instantiation).

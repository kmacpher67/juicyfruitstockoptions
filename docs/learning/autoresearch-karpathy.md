# AutoResearch — Karpathy's Autonomous Experiment Framework

**Source:** [github.com/karpathy/autoresearch](https://github.com/karpathy/autoresearch)  
**Language:** Python | **Compute:** Single NVIDIA GPU (H100 tested)  
**Status:** Research/Scoping — Juicy Fruit adaptation planning only

---

## What Is autoresearch?

Karpathy's `autoresearch` gives an AI agent a small but real LLM training setup and lets it experiment autonomously overnight. The agent modifies code, trains for 5 minutes, checks if the result improved, keeps or discards, and repeats — producing a log of ~100 experiments while you sleep.

**Three files that matter:**
| File | Role | Who edits |
|---|---|---|
| `prepare.py` | Fixed data prep, evaluation utilities | Nobody (frozen) |
| `train.py` | Full GPT model, optimizer, training loop | **The AI agent** |
| `program.md` | Research instructions / agent context | **The human** |

**The metric:** `val_bpb` (validation bits per byte) — lower is better. Vocab-size-independent so architectural changes are fairly compared across iterations.

**The fixed time budget:** Every experiment runs for exactly 5 minutes wall clock, regardless of model size, batch size, or architecture changes. This makes experiments directly comparable.

---

## Core Loop (Simplified)

```
while True:
    agent modifies train.py (one targeted change)
    run training for exactly 5 minutes
    measure val_bpb
    if val_bpb < previous_best:
        keep change, update baseline
    else:
        revert change
    log result (iteration, config diff, metric delta, kept/discarded)
    repeat
```

The human only programs `program.md` — the "research org code" that tells the agent what to explore and how to reason about improvements.

---

## Is autoresearch Only for Code / LLM Training?

**No.** The framework is a specific implementation for LLM training optimization, but the *pattern* is broadly applicable:

```
modify one parameter → run fixed experiment → measure outcome → keep/discard → repeat
```

This is essentially autonomous hill-climbing with a human-readable audit log.

---

## How autoresearch Maps to Juicy Fruit

| autoresearch concept | Juicy Fruit equivalent |
|---|---|
| `train.py` (single editable file) | Scoring config document (weights, thresholds, multipliers) in `system_config` or a dedicated JSON |
| `val_bpb` (single metric to minimize) | Recommendation hit rate, or annualized yield delta (predicted vs actual) |
| 5-minute training budget | Backtest window (e.g., last 90 days of graded recommendations) |
| `program.md` (human-written instructions) | Juicy research context document pointing at our scoring algo goals |
| Experiment log | `score_optimizer_runs` Mongo collection: config snapshot, metric before/after, kept boolean |
| H100 GPU | Not needed — Juicy backtests run on MongoDB + Python (CPU only) |

---

## Three Juicy Applications

### 1. Recommendation Grader (Truth Engine) — Prerequisites First
Before any optimization loop, we need ground truth: **did our recommendations work?**

Every persisted `opportunities` record should gain an `outcome` subdocument:
- `outcome_at` — when graded
- `outcome_pnl` — realized P&L vs predicted yield
- `outcome_result` — `WIN / LOSS / EXPIRED_WORTHLESS / ASSIGNED / ROLLED / PENDING`

Relevant code: `app/services/opportunity_service.py`, `app/models/opportunity.py`, `app/scheduler/jobs.py`

The grader runs nightly and closes out opportunities past their DTE or evaluation window. Without this, there is nothing to measure in the optimization loop.

### 2. Scoring Parameter Self-Optimizer (autoresearch pattern)
Once graded history exists, the optimizer runs the autoresearch loop:

1. Modify one scoring parameter (IV weight, delta threshold, yield floor, liquidity penalty)
2. Backtest against last 90 days of graded recommendations
3. Measure: `hit_rate_delta` or `annualized_yield_improvement`
4. Keep if better, revert if worse
5. Log, repeat

The "single editable file" is a scoring config document — NOT production service code. Optimizer never touches live trading logic.

### 3. Strategy Comparator (A/B Experiments)
Run controlled experiments comparing strategy variants:
- "Sell ATM call 30 DTE" vs "Sell 10% OTM 45 DTE" vs "Diagonal spread"
- Measure hit rate, average realized yield, drawdown per strategy
- Produce leaderboard across graded history

---

## What autoresearch Is NOT Good For

- **Real-time trading decisions** — it's an offline optimization loop, not a live signal
- **Strategies with insufficient history** — need at least 50-100 graded outcomes per variant for statistical significance
- **Replacing human judgment** — it finds parameter improvements within the strategy structure Ken defines, not entirely new strategies
- **GPU-dependent workflows** — the Karpathy implementation requires NVIDIA GPU; our adaptation avoids this

---

## Key Design Principles to Preserve

1. **One metric.** Resist tracking 10 metrics simultaneously. Pick one (hit rate or yield delta) and optimize it cleanly. Add secondary metrics to the log for analysis but optimize only the primary.
2. **One change per iteration.** Each experiment modifies exactly one parameter or threshold. Multi-parameter changes make causation impossible to attribute.
3. **Fixed evaluation window.** The backtest window must be constant across iterations so results are comparable. "Last 90 days of graded recs" must not shift.
4. **Human-readable audit log.** Every iteration must be explainable: what changed, by how much, what happened to the metric, kept or discarded.
5. **Guardrails on scope.** The optimizer can only modify the isolated scoring config. It cannot touch live API routes, scheduler intervals, or portfolio logic.

---

## Relevant Existing Juicy Docs

| Doc | Relevance |
|---|---|
| [Opportunity Scoring](opportunity-scoring.md) | Defines current 0-100 rubric — this is what the optimizer would tune |
| [Opportunity Persistence & Grading](opportunity-persistence-and-grading.md) | Data persistence contract for graded outcomes |
| [Backtesting Engines](backtesting-engines.md) | Evaluation engine options for the optimization loop |
| [Agent Frameworks](agent-frameworks.md) | LangChain / Lumibot context for orchestrating the agent loop |

---

## Relevant Codebase Touchpoints

| File | Role in autoresearch adaptation |
|---|---|
| `app/services/opportunity_service.py` | Scoring logic — parameter target for optimizer |
| `app/services/scanner_service.py` | Master scan orchestration — feeds recommendation candidates |
| `app/models/opportunity.py` | Pydantic model — needs `outcome` subdocument added |
| `app/scheduler/jobs.py` | Grader job and optimizer loop entry point |
| `app/utils/greeks_calculator.py` | Greeks inputs to scoring — candidate optimization target |

---

## Open Questions / Scoping Needed

1. **Time horizon for "win"** — DTE-based (expired worthless = full premium captured = WIN)? Or fixed N-day P&L window?
2. **Data readiness** — how many historical `opportunities` records exist with resolvable outcomes? Run `db.opportunities.countDocuments({})` to check.
3. **Single metric choice** — hit rate (binary win/loss) vs annualized yield delta (continuous, noisier but more informative)?
4. **Agent autonomy** — semi-autonomous (suggest changes, Ken approves) vs fully autonomous overnight loop?
5. **Compute** — confirm no GPU needed for Juicy adaptation; all evaluation runs on existing MongoDB + Python stack.

---

*Last updated: 2026-04-19 | Status: Research/Scoping*

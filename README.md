# BSDI Project AI Agent — Tracks A, B, and C

Complete agentic AI workflows over the PMTS Projects List (Government of Balochistan development portfolio).

- **Track A — Query Agent:** natural-language plan → tool → observe → answer loop.
- **Track B — Audit Agent:** autonomous check planning, independent audit tools, and prioritized synthesis.
- **Track C — Multi-Agent Review Board:** Finance, Delivery, Equity, and Coordinator agents.

> "We have an extra PKR 2 billion. Which currently `Not Started` projects should be
> funded first, and why?"

A Coordinator agent dispatches structured tasks to three specialist agents (Finance,
Delivery, Equity), collects their evidence-backed findings, resolves visible
disagreements between them, ranks every `Not Started` project with a transparent
scoring model, and selects a funding shortlist that never exceeds the budget cap.

---

## 1. Project Description

The dataset (`data/Projects.xlsx`) contains 4,083 real public development projects
across 39 districts of Balochistan, worth ~PKR 51.5 billion, and is deliberately
messy (duplicated contractor prefixes, six phone number formats, agency name
variants, ~82% missing start dates, etc.). This system:

- Loads and cleans the file without crashing on or silently fixing messy rows.
- Runs three specialist agents (Finance / Delivery / Equity) that each investigate
  the portfolio using real tool calls, never a single prompt.
- Has a Coordinator that combines their findings, detects genuine data-driven
  trade-offs, and produces a ranked, budget-constrained funding shortlist.
- Never invents a project ID, cost, or statistic — every number is computed by
  Python and traceable back to a specific tool call.

## 2. All Track Requirements — Mapping

| Requirement | Where it's satisfied |
|---|---|
| Track A grounded question answering | `agents/query_agent.py`; uses `filter_projects`, `aggregate_projects`, `group_projects`, and `get_project` in a visible loop |
| Track A four mandatory query shapes | Cross-filter count, filtered budget total, ranked group aggregation, and sorted top-N rows are covered by automated tests |
| Track B autonomous planning | `agents/audit_agent.py` asks the live LLM to select ≥4 checks from independently callable tools |
| Track B ≥4 issue classes | `tools/audit_tools.py`: missing start date, high-cost/no contractor, high Not-Started share, category outliers, and tender mismatch |
| Track B prioritized synthesis | Audit results include counts/examples and are passed to a separate grounded synthesis step |
| ≥3 specialist agents + 1 coordinator | `agents/finance_agent.py`, `delivery_agent.py`, `equity_agent.py`, `coordinator_agent.py` |
| Structured agent-to-agent messages | `models/messages.py` (`AgentReport`, `AgentFinding`, `ConflictRecord`, `FinalReport`) — no free-form text parsing |
| Each specialist grounds claims in queried data | Every finding carries `Evidence` objects naming the source tool; agents can only reach data through named tools |
| Coordinator cites which agent raised which concern | `FinalReport.finance_findings` / `.delivery_findings` / `.equity_findings`, each attributed to `agent_name` |
| Visible disagreement / trade-off resolved | `CoordinatorAgent._detect_conflicts()` — computed live from per-candidate sub-scores, never hardcoded |
| Genuine agent-to-agent communication (not one prompt) | Each specialist runs its own independent PLAN→ACT→OBSERVE→REASON loop with its own tool registry before returning to the Coordinator |
| Handles messy/missing data without breaking | `data_processing/`, 42 passing tests including edge cases |

## 3. Features

- Real plan → act → observe → reason → stop agent loop per specialist, plus a
  second-level Coordinator loop.
- 10 documented, reusable tools (Section 6 of the assignment brief) shared across
  agents.
- Transparent, documented multi-factor scoring (35% Finance / 35% Delivery / 30%
  Equity) for ranking `Not Started` candidates.
- Hard budget-cap + district/category concentration limits enforced in Python,
  never by the LLM.
- Demo Mode: the entire system runs with zero API key, using real data and real
  tool calls, with deterministic (not LLM-driven) synthesis.
- Streamlit dashboard: dataset overview, charts, data-quality report, live agent
  activity panel, final report with CSV/Markdown export.
- 45 automated tests covering loading, cleaning, all three tracks, tools, agents, and the budget
  constraint.
- Full run logging to `run_logs/*.json` for auditability.

## 4. Architecture

See `docs/writeup.md` for the full architecture diagram and design rationale, and
`orchestration/graph.py` for the orchestration flow documented alongside the code.

```text
USER → Coordinator → {Finance, Delivery, Equity} agents → tools/ → real DataFrame
                    → rank_funding_candidates() → select_within_budget()
                    → conflict detection → FinalReport
```

## 5. Agent Descriptions

- **Finance Agent** (`agents/finance_agent.py`): cost structure, budget
  concentration, IQR-based cost outliers (computed within each category), and the
  financial exposure of `Not Started` projects by category.
- **Delivery Agent** (`agents/delivery_agent.py`): six independent delivery-risk
  checks — missing start dates, low progress, missing XEN, missing contractor,
  NITs/status mismatches, and stalled high-cost projects.
- **Equity Agent** (`agents/equity_agent.py`): district/category budget
  concentration and under-allocation, using only measurable shares — never
  inferred poverty or need.
- **Coordinator Agent** (`agents/coordinator_agent.py`): dispatches tasks,
  collects reports, runs its own ranking/selection tool calls, detects and
  resolves conflicts, and writes the final report.

## 6. Tool Descriptions

| Tool | File | Purpose |
|---|---|---|
| `load_projects` | `tools/data_loader.py` | Load & cache the cleaned dataset |
| `filter_projects` | `tools/query_tools.py` | Filtered, capped row-level query |
| `aggregate_projects` | `tools/query_tools.py` | count/sum/avg/median/min/max |
| `district_statistics` | `tools/finance_tools.py` | Per-district budget & pipeline stats |
| `category_statistics` | `tools/finance_tools.py` | Per-category budget & pipeline stats |
| `find_cost_outliers` | `tools/finance_tools.py` | IQR outliers within category |
| `find_delivery_risks` | `tools/delivery_tools.py` | 6 delivery/accountability risk checks |
| `find_equity_risks` | `tools/equity_tools.py` | District/category concentration checks |
| `get_project` | `tools/query_tools.py` | Full record for one Global ID |
| `rank_funding_candidates` / `select_within_budget` | `tools/ranking_tools.py` | Transparent scoring + budget-constrained selection |
| `get_data_quality_report` | `tools/data_quality_tools.py` | Portfolio-wide messiness report |

## 7. Dataset Information

- File: `data/Projects.xlsx`, sheet `Projects List`, header on row 4 (3-row banner
  skipped).
- ~4,083 rows, 39 districts, 13 categories, ~PKR 51.5B total portfolio.
- Known messiness: duplicated `M/S` contractor prefixes, 6 phone number formats,
  agency name variants (LG/LGRD/Local Govt, PHE/PHED, CWPP&H/C&WPP&H), ~82% missing
  start dates, ~73% missing contractor, ~64% missing XEN.

## 8. Installation (Windows)

```powershell
cd pmts-multi-agent-review-board
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## 9. Environment Variables

Copy `.env.example` to `.env` and fill in your xAI API key:

```powershell
copy .env.example .env
notepad .env
```

```env
LLM_PROVIDER=grok
XAI_API_KEY=xai-your-api-key-here
XAI_MODEL=grok-4-latest
XAI_BASE_URL=https://api.x.ai/v1/chat/completions
DEMO_MODE=false
```

Create an API key in the xAI Console at https://console.x.ai/. Keep it only in
`.env`; never paste it into source code or commit it. If your chosen
`XAI_MODEL` isn't reachable, the app automatically falls back to Demo Mode and
shows the API error. Chat requires a working xAI key.

## 10. Running

```powershell
python -m streamlit run app.py
```

Then open the local URL Streamlit prints (usually `http://localhost:8501`).

## 11. Running in Demo Mode

No API key needed:

```powershell
set DEMO_MODE=true
streamlit run app.py
```

(or set `DEMO_MODE=true` in `.env`). Demo Mode still loads and cleans the real
Excel file and runs every real tool call — only the LLM call itself is skipped in
favor of each agent's documented, fixed investigation plan.

## 12. Example Workflow

1. Open the app — Section 1 shows live dataset totals (projects, portfolio value,
   status breakdown) computed from the Excel file.
2. Expand "Data Quality Report" to see missing-value counts and normalization
   examples.
3. Click **"Run Multi-Agent Review"**.
4. Watch the Agent Activity Panel show the Coordinator dispatching each specialist,
   each specialist's own tool calls, and the Coordinator's ranking/selection steps.
5. Review the Final Report: executive summary, budget summary, ranked recommended
   projects table, per-project explainability, specialist findings tabs, and the
   Conflicts & Trade-offs tab.
6. Download the shortlist as CSV or the full report as Markdown.

## 13. Data Cleaning Strategy

See `data_processing/normalizer.py` and `cleaner.py`. Every normalization function
preserves the raw value alongside the cleaned one. Agency name variants use an
explicit, documented mapping (not fuzzy matching) to avoid silently merging
different agencies. Phone numbers are only normalized when the digit pattern
confidently matches a known Pakistani format; anything else is flagged
`needs_review` rather than guessed.

## 14. Anti-Hallucination Strategy

See `docs/writeup.md` §"How Hallucination Is Prevented" for the full explanation.
In short: agents can only reach data through named tools; all arithmetic happens in
Python; missing values stay missing; statistically fragile computations (e.g. IQR
on tiny groups) are skipped rather than faked; every finding carries traceable
`Evidence`.

## 15. Scoring Methodology

Documented in full in `tools/ranking_tools.py`. Summary:

```
FinalScore = 0.35 × FinanceScore + 0.35 × DeliveryScore + 0.30 × EquityScore
```

- **FinanceScore**: 60% cost feasibility (cheaper = higher) + 40% category need
  (share of that category's own budget still Not Started).
- **DeliveryScore**: starts at 100, penalized -25 for no tender issued, -20 for no
  XEN assigned, -15 for no executing agency recorded.
- **EquityScore**: higher for districts with a lower existing share of total
  portfolio budget.

`select_within_budget()` then greedily selects down the ranked list, skipping any
candidate that would exceed the budget cap or push a single district/category
above a documented concentration limit.

## 16. Agent Communication

All inter-agent communication uses Pydantic models (`models/messages.py`) — never
free-form text parsing. See `docs/writeup.md` for detail.

## 17. Conflict Resolution

`CoordinatorAgent._detect_conflicts()` flags any selected project whose
Finance/Delivery/Equity sub-scores disagree (one dimension weak <55, another strong
>70) and writes a resolution referencing the documented scoring weights. See
`docs/writeup.md`.

## 18. Testing

```powershell
python -m pytest tests/ -v
```

42 tests across `test_data_loader.py`, `test_tools.py`, `test_agents.py`,
`test_budget.py`, `test_data_quality.py`. All passing as of this submission.

## 19. Transcript Generation

```powershell
python generate_transcripts.py
```

Regenerates `transcripts/run_01.md`, `run_02.md`, `run_03.md` from real executions
(three different funding envelopes: PKR 1B / 2B / 3B). Uses your configured LLM if
`HF_TOKEN` is set (the legacy `HF_API_TOKEN` name is also accepted), otherwise Demo Mode — either way, all dataset numbers are
real, never fabricated.

## 20. Limitations

- The Hugging Face free Inference API has rate limits and not all models are
  hosted; Demo Mode is the reliable fallback for grading.
- Equity findings are limited to what's measurable in this dataset (budget/project
  shares) — they are not an independent needs assessment.
- Contractor normalization concatenates joint-contract firm names as-is rather than
  splitting them, since splitting would require guessing which text belongs to
  which firm.
- `select_within_budget()` is a greedy selection over the ranked list, not a
  globally-optimal knapsack solution — documented as a deliberate simplicity
  trade-off for a viva-friendly codebase.

## 21. Academic Integrity Note

This codebase was built with AI assistance per the assignment's stated policy. Every
file is commented to explain *why* it exists and how it works, and `docs/writeup.md`
plus the "How I'd explain this in a viva" section below are written so the author
can explain and defend every line.

---

## How I Would Explain This Project in a Viva

**1. What makes this system agentic?**
Each agent decides which tools to call and in what order based on what it observes,
not a fixed script written by a human for every question. The Coordinator itself
decides to re-query (`rank_funding_candidates`, `select_within_budget`) after seeing
the specialists' reports, rather than following one linear prompt.

**2. Why are there multiple agents?**
Financial feasibility, delivery readiness, and equity are genuinely different lenses
on the same data, often in tension. Splitting them into separate agents with
separate tool access forces each concern to be argued on its own evidence before
being reconciled, instead of one prompt silently averaging everything together.

**3. How does the Finance Agent work?**
It calls `category_statistics`, `find_cost_outliers` (IQR within category), and
`aggregate_projects` to build a picture of cost structure and Not-Started financial
exposure, then writes findings citing those exact numbers.

**4. How does the Delivery Agent work?**
It calls `find_delivery_risks`, which runs six independent, documented checks
(missing start date, low progress, missing XEN, missing contractor, NITs mismatch,
stalled high-cost) and groups the results into findings by risk type.

**5. How does the Equity Agent work?**
It calls `find_equity_risks` and `district_statistics` to measure budget
concentration and under-allocation as percentages — strictly comparative, never a
judgment about a district's socioeconomic status.

**6. How does the Coordinator resolve disagreement?**
`rank_funding_candidates` gives every candidate three sub-scores (0–100). If a
selected project is weak (<55) on one dimension but strong (>70) on another, that's
flagged as a real trade-off, and the resolution explains the decision using the
documented 35/35/30 weighting.

**7. How do you prevent hallucination?**
Agents never see raw data, only tool outputs; all arithmetic is in Python; missing
values stay missing (never zero-filled); every finding cites its source tool.

**8. Why don't you send the whole Excel file to the LLM?**
4,083 rows would be slow, expensive, and push the model toward guessing/averaging
instead of computing exact aggregates. Tools return only the small, already-computed
answer the agent actually needs.

**9. How is the PKR 2 billion constraint enforced?**
In Python, in `select_within_budget()` — it's a hard `if spent + cost > cap: skip`,
not something the LLM is asked to respect.

**10. What happens when data is missing?**
It's preserved as missing (e.g. `cost_m = NaN`, not `0`), reported in the Data
Quality Report, and used as a documented penalty signal in delivery scoring (e.g.
no XEN → -20 points) rather than silently ignored.

**11. What happens if the API fails?**
`agents/llm_provider.py::get_provider()` catches initialization failures and any
call failures are surfaced; the app is designed to be run in Demo Mode as a reliable
fallback that needs no network access to the LLM at all.

**12. What was the biggest limitation?**
See `docs/reflection.md` — small-category IQR computations initially produced
statistically meaningless outlier flags; fixed with a minimum-group-size guard.

---

## 22. Files You Should Submit

```
pmts-multi-agent-review-board/
├── app.py, generate_transcripts.py, requirements.txt, .env.example, .gitignore, README.md
├── data/Projects.xlsx
├── agents/, tools/, models/, data_processing/, orchestration/
├── tests/
├── transcripts/run_01.md, run_02.md, run_03.md
├── docs/writeup.md, docs/reflection.md
└── run_logs/  (generated at runtime; safe to omit or include a sample)
```
"# Agentic-AI-Assistant" 
"# Agentic-AI-Assistant" 
"# Agentic-AI-Assistant" 
"# Agentic-AI-Assistant" 

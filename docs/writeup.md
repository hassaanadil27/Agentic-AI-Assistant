# Write-up: PMTS Multi-Agent Review Board (Track C)

## Architecture

```text
                          USER (Streamlit UI)
                                 |
                                 v
                      COORDINATOR AGENT (agents/coordinator_agent.py)
                                 |
              +------------------+------------------+
              |                  |                  |
              v                  v                  v
        FINANCE AGENT      DELIVERY AGENT      EQUITY AGENT
              |                  |                  |
              v                  v                  v
        finance_tools.py   delivery_tools.py   equity_tools.py
              |                  |                  |
              +------------------+------------------+
                                 |
                                 v
                 rank_funding_candidates() + select_within_budget()
                          (tools/ranking_tools.py)
                                 |
                                 v
                    _detect_conflicts()  ->  FinalReport
```

Every agent (`agents/base_agent.py`) implements a genuine
**plan → act → observe → reason → … → stop** loop:

- **LLM mode** (Hugging Face Inference API): the model is given a system
  prompt describing its role and its tools, then drives the loop itself
  by emitting one JSON action per turn (`call_tool` or `final_answer`).
  Python executes each tool call and feeds the JSON result back. This is
  necessary because most open Hugging Face chat models don't support
  native function calling the way Anthropic/OpenAI APIs do — a
  structured-JSON prompting protocol is the standard workaround.
- **Demo Mode** (no API key required): each agent instead runs its own
  fixed, documented investigation plan — still calling the exact same
  real tools against the real dataset — and synthesizes findings with
  rule-based text generation. No dataset numbers are ever invented in
  either mode; the LLM (when used) only ever reasons over numbers Python
  already computed.

The Coordinator itself runs a second-level loop: it dispatches structured
tasks to the three specialists, collects their `AgentReport` objects,
makes its **own** additional tool calls (`rank_funding_candidates`,
`select_within_budget`), reasons over the combined evidence to detect
conflicts, and synthesizes the final `FinalReport`.

## How Hallucination Is Prevented

1. **No agent ever sees the raw Excel file or the full DataFrame.** Every
   agent can only reach data through named tools (`filter_projects`,
   `district_statistics`, etc.), each of which returns small, structured,
   already-computed results.
2. **All arithmetic happens in Python**, never in the LLM — counts, sums,
   medians, IQR fences, and the funding scoring formula are all computed
   in `tools/`. The LLM (in live mode) is instructed that every numeric
   claim must trace back to an observed tool result.
3. **Missing data is preserved as missing**, never filled with 0 or a
   guess (`data_processing/normalizer.py::safe_float` returns `None` on
   failure, not `0`).
4. **Statistically fragile computations are skipped, not faked** — e.g.
   `find_cost_outliers()` refuses to compute IQR fences for categories
   with fewer than 5 projects (see `docs/reflection.md`).
5. **Every finding carries `Evidence` objects** naming the source tool,
   so every claim in the final report is traceable back to a specific
   tool call (Section 19, traceability).

## Failure Hit While Building

See `docs/reflection.md` — small-sample IQR groups initially produced
statistically meaningless "outliers"; fixed with a documented minimum
group-size threshold.

## Track C Requirement: Agent Communication & Conflict Resolution

Agents communicate exclusively through Pydantic models
(`models/messages.py`: `AgentReport`, `AgentFinding`, `ConflictRecord`,
`FinalReport`) — never through free-form text parsing. The Coordinator's
`_detect_conflicts()` method inspects the **per-candidate sub-scores**
(Finance/Delivery/Equity, each 0–100) that `rank_funding_candidates()`
computed for every selected project. Any selected project where one
dimension scores below 55 while another scores above 70 is flagged as a
genuine, data-driven trade-off — e.g. a project may be Equity-favorable
(serves an under-allocated district) yet Delivery-weak (no XEN assigned,
no tender issued). The Coordinator's resolution text explains, using the
documented 35/35/30 weighting, why the project was still selected (or
would be rejected), and what should be fixed before disbursement. This
mechanism is entirely derived from the live-computed scores — it is not
hardcoded to any specific project, so it will surface different
conflicts if the underlying dataset changes.

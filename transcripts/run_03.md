# Run 03 — Expanded PKR 3B Funding Round

**Mode:** Demo Mode (deterministic, rule-based reasoning over real tool results)
**Funding envelope:** PKR 3,000M
**Dataset:** 4083 projects, PKR 51,550.1M total portfolio, 39 districts

## Agent Plan & Tool Calls (Agent Activity Panel)

```text
[Coordinator] PLAN: load dataset, dispatch Finance/Delivery/Equity reviews, then rank & select Not Started candidates within the PKR 3000M funding envelope.
[Coordinator] Dataset loaded: 4083 projects, 51550.1M total portfolio, 39 districts.
[Coordinator] ACT: dispatching structured task to Finance Agent.
[Finance Agent] Received task: Assess financial structure and cost outliers relevant to a PKR 2,000M Not-Started funding round.
[Finance Agent] PLAN: (1) portfolio totals (2) category budget shares (3) cost outliers (4) Not-Started financial exposure by category.
[Finance Agent] Calling aggregate_projects({'operation': 'total_cost', 'status': 'Not Started'})
[Finance Agent] aggregate_projects -> count=1003
[Finance Agent] Calling category_statistics({})
[Finance Agent] category_statistics -> 13 item(s) returned
[Finance Agent] Calling find_cost_outliers({'status': None})
[Finance Agent] find_cost_outliers -> 30 item(s) returned
[Coordinator] ACT: dispatching structured task to Delivery Agent.
[Delivery Agent] Received task: Assess delivery readiness and accountability risk across the portfolio, especially for Not Started projects.
[Delivery Agent] PLAN: (1) run full delivery risk sweep (2) group by risk type (3) assess overall procurement readiness for Not Started projects.
[Delivery Agent] Calling find_delivery_risks({})
[Delivery Agent] find_delivery_risks -> 135 item(s) returned
[Delivery Agent] Calling aggregate_projects({'operation': 'count', 'status': 'Not Started'})
[Delivery Agent] aggregate_projects -> count=1003
[Delivery Agent] Calling filter_projects({'status': 'Not Started', 'limit': 1})
[Delivery Agent] filter_projects -> count=1003
[Coordinator] ACT: dispatching structured task to Equity Agent.
[Equity Agent] Received task: Assess district and category budget concentration/under-allocation for a fair funding decision.
[Equity Agent] PLAN: (1) district budget shares (2) category concentration (3) districts with high Not-Started share (execution lag) (4) under-allocated districts.
[Equity Agent] Calling find_equity_risks({})
[Equity Agent] find_equity_risks -> 4 item(s) returned
[Equity Agent] Calling district_statistics({})
[Equity Agent] district_statistics -> 39 item(s) returned
[Coordinator] OBSERVE: collected 3 structured specialist reports.
[Coordinator] ACT: calling rank_funding_candidates() to score all Not Started projects.
[Coordinator] OBSERVE: 1003 Not Started candidates scored.
[Coordinator] ACT: calling select_within_budget() to enforce the PKR 3000M cap and district/category concentration limits.
[Coordinator] OBSERVE: selected 476 projects totaling 2999.64M (remaining 0.36M).
[Coordinator] REASON: scanning selected candidates for cross-specialist disagreement.
[Coordinator] REASON: 15 visible conflict(s)/trade-off(s) identified and resolved.
[Coordinator] STOP: final recommendation generated.
```

## Final Output

### Executive Summary
Reviewed 4083 projects (total portfolio 51,550.1M PKR). Out of all 'Not Started' candidates, the board recommends funding 476 projects totaling 2,999.64M PKR against the 3,000M PKR envelope (remaining 0.36M). Selections balance financial feasibility, delivery readiness, and district/category equity using a transparent, weighted scoring model (35% Finance / 35% Delivery / 30% Equity). 15 specific trade-off(s) between specialists were identified and resolved during ranking (see Conflicts & Trade-offs).

### Budget Summary
- Budget Available: PKR 3,000.0M
- Recommended: PKR 2,999.64M
- Remaining: PKR 0.36M
- Projects Selected: 476

### Top 10 Recommended Projects

| Rank | Global ID | Project | District | Category | Cost (M) | Score |
|---|---|---|---|---|---:|---:|
| 1 | BARS-0016-P3 | Installation of Solar Street lights at Ibrahi | Barshore | Municipal | 18.0 | 64.0 |
| 2 | TUM-0041-P3 | Construction of box culvert 2x2.50x1.50 Balic | Tump | Road | 5.2 | 63.8 |
| 3 | BARS-0038-P3 | Repair/Rehabilitation of 02 x Police Thanas,  | Barshore | Security | 15.0 | 63.5 |
| 4 | BARS-0001-P3 | Repair & Rehab of No. 7 to 8 (Abandoned Govt. | Barshore | Building | 10.0 | 63.4 |
| 5 | BARS-0002-P3 | Repair & Rehab of No. 4 to 6 (Abandoned Govt. | Barshore | Building | 10.0 | 63.4 |
| 6 | BARS-0003-P3 | Repair & Rehab of No. 1 to 3 (Abandoned Govt. | Barshore | Building | 10.0 | 63.4 |
| 7 | UDER-0018-P3 | WSS at Killi Maskeef | Upper Dera Bugti | PHE | 9.0 | 62.5 |
| 8 | UDER-0024-P3 | WSS at Phelawagh Market | Upper Dera Bugti | PHE | 9.0 | 62.5 |
| 9 | UDER-0025-P3 | WSS at Killi Dilgowash | Upper Dera Bugti | PHE | 9.0 | 62.5 |
| 10 | UDER-0026-P3 | WSS at CM House Qadirababd | Upper Dera Bugti | PHE | 9.0 | 62.5 |

*(+ 466 more projects in the full run — see CSV export in the app)*

### Sample Finance Finding
**[MEDIUM] Total financial exposure of Not Started projects**  
Across the portfolio, Not Started projects total 12427.96M PKR across 1003 projects -- this is the pool the PKR 2,000M funding decision will be drawn from.

### Sample Delivery Finding
**[HIGH] In-Progress projects with no recorded start date (25 found)**  
Status is 'In Progress' but no Work Started date is recorded. This pattern was found in 25 project(s) portfolio-wide.

### Sample Equity Finding
**[MEDIUM] Districts where a large share of their own budget is still Not Started (3 found)**  
66.7% of Chaghi's 87 projects are still 'Not Started' (58 projects, 655.2M budget).; 62.9% of Loralai's 70 projects are still 'Not Started' (44 projects, 401.0M budget).; 100.0% of Upper Dera Bugti's 37 projects are still 'Not Started' (37 projects, 571.2M budget).

### Conflicts & Trade-offs (sample)
- **Issue:** Trade-off on NUS-0025-P3 (Construction of Parking/ Staging Area Near Kuchaki)
  - Finance: Favorable: cost 5.0M fits within budget (Finance score 71).
  - Delivery: Neutral (Delivery score 55).
  - Equity: Cautious: district already has a larger existing share (Equity score 42).
  - **Resolution:** Coordinator ranked NUS-0025-P3 at 56.7/100 using the documented 35% Finance / 35% Delivery / 30% Equity weighting. Despite weakness in equity, strength in finance kept it within the funded shortlist; the weak dimension(s) should be addressed before disbursement.
- **Issue:** Trade-off on SOH-0105-P3 (Construction of a bridge on Manjhoti Shakh Goth Humza Khan ()
  - Finance: Favorable: cost 5.0M fits within budget (Finance score 71).
  - Delivery: Neutral (Delivery score 55).
  - Equity: Cautious: district already has a larger existing share (Equity score 39).
  - **Resolution:** Coordinator ranked SOH-0105-P3 at 55.9/100 using the documented 35% Finance / 35% Delivery / 30% Equity weighting. Despite weakness in equity, strength in finance kept it within the funded shortlist; the weak dimension(s) should be addressed before disbursement.
- **Issue:** Trade-off on HUB-0043-P3 (Construction of Boundary wall for doda goth hospital and Lyi)
  - Finance: Favorable: cost 17.0M fits within budget (Finance score 70).
  - Delivery: Neutral (Delivery score 55).
  - Equity: Cautious: district already has a larger existing share (Equity score 35).
  - **Resolution:** Coordinator ranked HUB-0043-P3 at 54.4/100 using the documented 35% Finance / 35% Delivery / 30% Equity weighting. Despite weakness in equity, strength in finance kept it within the funded shortlist; the weak dimension(s) should be addressed before disbursement.

### Data Quality Warnings
- 2996 project(s) missing a contractor.
- 2595 project(s) missing an XEN (responsible engineer).
- 3331 project(s) missing a Work Started date.

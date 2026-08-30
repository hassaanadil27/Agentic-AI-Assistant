"""Professional, deterministic formatting for Track A analytical results."""
from __future__ import annotations
from typing import Any

from models.analysis import AnalysisResult
from tools.analysis_tools import NUMERIC_COLUMNS, _apply_filters
from tools.data_loader import get_dataframe


def metric(value: Any, kind: str | None = None) -> str:
    if value is None: return "Not recorded in dataset"
    if kind == "money": return f"PKR {float(value):,.2f} million"
    if kind == "percent": return f"{float(value):,.2f}%"
    if kind == "points": return f"{float(value):,.2f} percentage points"
    if isinstance(value, (int, float)) and float(value).is_integer(): return f"{int(value):,}"
    return str(value)


def format_professional_answer(result: AnalysisResult) -> str:
    evidence, plan = result.evidence, result.plan
    if not evidence or not plan: return result.answer
    df = get_dataframe()
    filtered, _ = _apply_filters(df, plan)
    lines: list[str] = []
    if plan.intent == "lookup" and result.table:
        row=result.table[0]
        lines=["## Project Details",""]
        fields=[("Project ID","global_id",None),("Project Name","description",None),("District","district",None),("Sector","category",None),("Status","status",None),("Progress","progress_pct","percent"),("Cost","cost_m","money"),("Executing Agency","executing_agency",None),("Start Date","work_started",None),("Contractor","contractor_normalized",None),("XEN","xen_name",None),("NITs","nits",None)]
        for label,key,kind in fields:
            value=row.get(key); shown="Not recorded in dataset" if value is None or str(value).strip()=="" else metric(value,kind)
            lines.append(f"- **{label}:** {shown}")
    elif plan.intent == "records" or (plan.operation == "list" and plan.target_column == "global_id"):
        direction="Highest" if plan.sort=="descending" else "Lowest" if plan.sort=="ascending" else "Matching"
        lines=[f"## {direction} Ranked Projects","",f"- **Matching Projects:** {len(filtered):,}",f"- **Showing:** {len(result.table):,}",f"- **Sorted By:** {(plan.target_column or 'dataset order').replace('_',' ').title()} ({plan.sort})",""]
        for index,row in enumerate(result.table,1):
            lines += [f"{index}. **{row.get('global_id','Not recorded')} — {row.get('description','Not recorded')}**",f"   - District: {row.get('district') or 'Not recorded'}",f"   - Status: {row.get('status') or 'Not recorded'}",f"   - Progress: {metric(row.get('progress_pct'),'percent')}",f"   - Cost: {metric(row.get('cost_m'),'money')}"]
    elif plan.intent == "group" and len(plan.group_by)==1:
        group=plan.group_by[0]; kind="money" if plan.target_column=="cost_m" else "percent" if plan.operation=="percentage" or plan.target_column=="progress_pct" else None
        lines=[f"## {group.replace('_',' ').title()} Analysis","",result.answer,""]
        for index,row in enumerate(result.table,1):
            lines.append(f"{index}. **{row.get(group)}:** {metric(row.get('value'),kind)}")
            if row.get("record_count") is not None: lines.append(f"   - Records: {int(row['record_count']):,}")
            if row.get("total_cost_m") is not None: lines.append(f"   - Total Cost: {metric(row['total_cost_m'],'money')}")
        if len(result.table)==2:
            a,b=result.table; difference=float(a["value"])-float(b["value"])
            lines += ["","## Key Difference","",f"- **{a[group]} vs {b[group]}:** {metric(abs(difference),'money' if plan.target_column=='cost_m' else 'points' if plan.target_column=='progress_pct' else None)} {('higher' if difference>=0 else 'lower')} for {a[group]}."]
            if group == "district":
                names=[str(a[group]),str(b[group])]; subset=filtered[filtered["district"].isin(names)]
                counts=subset.groupby(["status","district"]).size().unstack(fill_value=0)
                lines += ["","## Status Breakdown","",f"| Status | {names[0]} | {names[1]} |","|---|---:|---:|"]
                for status in sorted(counts.index): lines.append(f"| {status} | {int(counts.at[status,names[0]]) if names[0] in counts else 0:,} | {int(counts.at[status,names[1]]) if names[1] in counts else 0:,} |")
    else:
        value=result.table[0].get("Value") if result.table else None
        total=len(df); matching=len(filtered); share=matching/total*100 if total else 0
        label={"count":"Matching Projects","distinct_count":f"Distinct {(plan.target_column or 'value').replace('_',' ')}s","sum":"Total Project Cost","mean":"Average Project Cost" if plan.target_column=="cost_m" else "Average Progress","median":"Median","min":"Minimum","max":"Maximum","percentage":"Portfolio Share"}.get(plan.operation,"Result")
        kind="money" if plan.target_column=="cost_m" else "percent" if plan.target_column=="progress_pct" or plan.operation=="percentage" else None
        lines=["## Answer","",f"- **{label}:** {metric(value,kind)}"]
        if plan.operation=="count":
            lines += [f"- **Total Portfolio:** {total:,} projects",f"- **Portfolio Share:** {share:.2f}%",f"- **Remaining Outside Filter:** {total-matching:,} projects"]
        elif plan.operation in {"sum","mean","median","min","max","std"} and plan.target_column in NUMERIC_COLUMNS:
            series=filtered[plan.target_column].dropna()
            lines += [f"- **Projects Analyzed:** {len(series):,}",f"- **Average:** {metric(series.mean(),kind)}",f"- **Median:** {metric(series.median(),kind)}",f"- **Minimum:** {metric(series.min(),kind)}",f"- **Maximum:** {metric(series.max(),kind)}"]
        if plan.operation=="percentage": lines += ["","## Calculation","",f"- {matching:,} ÷ {total:,} × 100 = **{share:.2f}%**"]
    if evidence.filters:
        operators={"eq":"=","ne":"≠","gt":">","gte":"≥","lt":"<","lte":"≤","in":"in","contains":"contains"}
        lines += ["","## Filters Applied",""]
        for item in evidence.filters:
            value=", ".join(map(str,item["value"])) if isinstance(item["value"],list) else item["value"]
            lines.append(f"- **{item['column'].replace('_',' ').title()}:** {operators.get(item['operator'],item['operator'])} **{value}**")
    lines += ["","## Evidence","",f"- **Dataset:** `{evidence.dataset}`",f"- **Records Analyzed:** {evidence.rows_analyzed:,} of {evidence.rows_available:,}",f"- **Matching Records:** {len(filtered):,}",f"- **Fields Used:** {', '.join(f'`{c}`' for c in evidence.columns)}",f"- **Operation:** `{evidence.operation}`"]
    if plan.operation=="count": lines += ["","## Insight","",f"- The matching projects represent **{len(filtered)/len(df)*100:.2f}%** of the recorded portfolio."]
    if evidence.missing_values_excluded: lines.append(f"- **Missing Numeric Values Excluded:** {evidence.missing_values_excluded:,}")
    return "\n".join(lines)


def validate_professional_answer(answer: str, result: AnalysisResult) -> tuple[bool, list[str]]:
    """Quality gate over the deterministic, tool-produced public response."""
    issues=[]
    if "## Evidence" not in answer: issues.append("missing evidence section")
    if not result.evidence or result.evidence.dataset not in answer: issues.append("dataset evidence missing")
    if result.plan and result.plan.filters:
        for condition in result.plan.filters:
            values=condition.value if isinstance(condition.value,list) else [condition.value]
            if any(str(value).casefold() not in answer.casefold() for value in values): issues.append(f"filter omitted: {condition.column}")
    if result.plan and result.plan.operation in {"sum","mean"} and result.plan.target_column=="cost_m" and "PKR" not in answer: issues.append("financial unit missing")
    if result.plan and result.plan.intent=="records" and result.table and not all(f"{i}. **" in answer for i in range(1,len(result.table)+1)): issues.append("numbered ranking missing")
    return not issues, issues

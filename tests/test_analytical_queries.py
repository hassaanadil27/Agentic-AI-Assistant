"""Acceptance coverage for unseen, evidence-grounded analytical questions."""
from __future__ import annotations

import math
import pandas as pd
import pytest

from agents.llm_provider import DemoProvider
from agents.query_agent import QueryAgent
from tools.data_loader import get_dataframe


@pytest.fixture(scope="module")
def agent():
    return QueryAgent(DemoProvider())


def _value(result):
    return result.table[0]["Value"]


def test_dataset_size(agent):
    result = agent.ask("How many projects are in the dataset?")
    assert _value(result) == len(get_dataframe()) and result.validation == "passed"


@pytest.mark.parametrize(("question", "operation", "expected"), [
    ("What is the average project cost?", "mean", lambda d: d.cost_m.mean()),
    ("What is the median progress?", "median", lambda d: d.progress_pct.median()),
    ("What is the minimum progress?", "min", lambda d: d.progress_pct.min()),
    ("What is the maximum project cost?", "max", lambda d: d.cost_m.max()),
    ("What is the standard deviation of project cost?", "std", lambda d: d.cost_m.std()),
])
def test_numeric_statistics(agent, question, operation, expected):
    result = agent.ask(question)
    assert result.plan["operation"] == operation
    assert math.isclose(float(_value(result)), float(expected(get_dataframe())), rel_tol=1e-4)


def test_multiple_filters(agent):
    df = get_dataframe()
    result = agent.ask("How many completed projects are in Health?")
    expected = len(df[(df.status == "Completed") & (df.category == "Health")])
    assert _value(result) == expected
    assert len(result.evidence["filters"]) == 2


def test_filtered_total(agent):
    df = get_dataframe()
    result = agent.ask("What is the total budget of Not Started projects?")
    assert math.isclose(float(_value(result)), float(df.loc[df.status == "Not Started", "cost_m"].sum()), rel_tol=1e-4)


def test_group_comparison_and_graph_share_data(agent):
    result = agent.ask("Compare project counts by sector")
    assert result.table == result.chart["data"]
    assert result.chart["type"] == "bar"
    assert sum(int(row["value"]) for row in result.table) == len(get_dataframe())


def test_two_value_comparison_uses_both_filters(agent):
    result = agent.ask("Compare average project cost for Completed and Not Started projects")
    assert result.plan["group_by"] == ["status"]
    assert result.plan["operation"] == "mean"
    assert {row["status"] for row in result.table} == {"Completed", "Not Started"}
    assert result.chart["data"] == result.table


def test_top_five_districts(agent):
    result = agent.ask("Show the top 5 districts by budget")
    expected = get_dataframe().groupby("district").cost_m.sum().sort_values(ascending=False).head(5)
    assert [row["district"] for row in result.table] == list(expected.index)


def test_bottom_sector(agent):
    result = agent.ask("Which sector has the fewest projects?")
    expected = get_dataframe().groupby("category").size().sort_values().index[0]
    assert result.table[0]["category"] == expected


def test_percentage_distribution(agent):
    result = agent.ask("What percentage of projects are in each status?")
    assert math.isclose(sum(float(row["value"]) for row in result.table), 100.0, rel_tol=1e-9)


def test_numeric_distribution(agent):
    result = agent.ask("Show the distribution of project cost")
    assert result.chart["type"] == "histogram"
    assert result.evidence["rows_analyzed"] == int(get_dataframe().cost_m.notna().sum())


def test_correlation(agent):
    df = get_dataframe()
    result = agent.ask("Is project cost correlated with progress?")
    assert result.chart["type"] == "scatter"
    assert math.isclose(float(_value(result)), float(df.cost_m.corr(df.progress_pct)), abs_tol=1e-4)


def test_numeric_condition_and_empty_result(agent):
    result = agent.ask("How many projects cost over 100 million?")
    assert result.validation == "failed"
    assert "No records" in result.answer
    assert not result.table and result.chart is None


def test_missing_contractor_filter(agent):
    result = agent.ask("How many projects have no contractor?")
    assert _value(result) == int((~get_dataframe().has_contractor).sum())


def test_list_distinct_values(agent):
    result = agent.ask("List all phases")
    assert {row["phase"] for row in result.table} == set(get_dataframe().phase.dropna().astype(str).unique())


def test_record_lookup(agent):
    result = agent.ask("Tell me about AWA-0130-P3")
    assert result.table[0]["global_id"] == "AWA-0130-P3"
    assert result.evidence["rows_analyzed"] == 1


def test_dynamic_schema(agent):
    result = agent.ask("What columns are available?")
    names = {row["name"] for row in result.table}
    assert {"global_id", "cost_m", "progress_pct", "category", "district"} <= names


def test_unknown_field_never_returns_default_number(agent):
    result = agent.ask("What is the average salary?")
    assert result.validation == "needs_clarification"
    assert not result.table and result.evidence is None
    assert "couldn't find" in result.answer


def test_followup_reuses_metric_and_adds_filter(agent):
    history = [
        {"role": "user", "content": "What is the average project cost?"},
        {"role": "assistant", "content": "The average was calculated from project cost."},
    ]
    result = agent.ask("Now only for completed projects", history)
    expected = get_dataframe().loc[get_dataframe().status == "Completed", "cost_m"].mean()
    assert result.plan["operation"] == "mean"
    assert math.isclose(float(_value(result)), float(expected), rel_tol=1e-4)


def test_project_architecture_uses_file_evidence(agent):
    result = agent.ask("How does the backend architecture work?")
    assert result.intent == "project_info" and result.validation == "passed"
    assert "api.py" in result.answer and "tools/analysis_tools.py" in result.answer


def test_no_successful_numeric_result_is_nan_or_infinite(agent):
    questions = ["average project cost", "median progress", "maximum project cost", "standard deviation of project cost"]
    for question in questions:
        result = agent.ask(question)
        assert result.validation == "passed"
        assert math.isfinite(float(_value(result)))


def test_immediate_attention_regression_never_falls_back_to_dataset_count(agent):
    result = agent.ask("which project needs immediate attention")
    assert result.intent == "attention_analysis"
    assert result.validation == "passed"
    assert result.table and result.table[0]["Project ID"] in set(get_dataframe().global_id)
    assert result.chart["data"] == result.table
    assert "project count" not in result.answer.casefold()
    assert result.plan["operation"] == "rank"
    assert "Observed reasons" in result.table[0]


@pytest.mark.parametrize(("question", "expected_intent"), [
    ("How many records are there?", "aggregate"),
    ("How many projects are there?", "aggregate"),
    ("Which project needs immediate attention?", "attention_analysis"),
    ("Which projects need attention right now?", "attention_analysis"),
    ("Which projects are at risk?", "attention_analysis"),
    ("Which project has the highest risk?", "attention_analysis"),
    ("Which project should we focus on first?", "attention_analysis"),
    ("Which project is performing worst?", "attention_analysis"),
    ("Which project has the lowest progress?", "records"),
    ("Which project has the highest progress?", "records"),
    ("Compare the two highest-risk projects", "attention_analysis"),
    ("Why does project KAL-0049-P2 need attention?", "attention_analysis"),
    ("What are the main problems with project AWA-0130-P3?", "attention_analysis"),
    ("Show me all overdue projects", "insufficient_data"),
    ("Show projects with critical risk", "insufficient_data"),
    ("Which project has improved the most?", "insufficient_data"),
    ("Which project is healthier?", "insufficient_data"),
    ("Which 5 projects should be started first?", "ranking"),
    ("Which sector has the highest total allocation?", "group"),
    ("Which district has the fewest projects?", "group"),
    ("Compare completed and not started project costs", "group"),
    ("Show projects with progress below 20", "aggregate"),
    ("What is the median cost in Health?", "aggregate"),
    ("List all project phases", "aggregate"),
    ("Show the cost distribution", "distribution"),
    ("Is cost related to progress?", "correlation"),
    ("Tell me about AWA-0130-P3", "lookup"),
    ("What fields are in the dataset?", "schema"),
    ("How does the backend work?", "project_info"),
    ("What is the model F1 score?", "project_info"),
])
def test_thirty_unseen_semantic_routes(agent, question, expected_intent):
    result = agent.ask(question)
    assert result.intent == expected_intent
    assert result.validation in {"passed", "needs_clarification"}
    assert "The **project count** is **4,083**" not in result.answer or question == "How many projects are there?"

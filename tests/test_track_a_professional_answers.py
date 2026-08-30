"""Acceptance tests for professional, evidence-rich Track A responses."""
import math
import pytest

from agents.llm_provider import DemoProvider
from agents.query_agent import QueryAgent
from tools.data_loader import get_dataframe


@pytest.fixture(scope="module")
def agent(): return QueryAgent(DemoProvider())


@pytest.mark.parametrize(("question","status"),[
    ("How many projects are completed?","Completed"),
    ("How many projects are in progress?","In Progress"),
    ("How many projects have not started?","Not Started"),
])
def test_status_counts_are_complete_and_evidenced(agent,question,status):
    result=agent.ask(question); expected=int((get_dataframe().status==status).sum())
    assert result.table[0]["Value"]==expected
    assert f"{expected:,}" in result.answer and "Portfolio Share" in result.answer
    assert status in result.answer and "## Evidence" in result.answer


def test_total_count(agent):
    result=agent.ask("How many projects are there?")
    assert result.table[0]["Value"]==len(get_dataframe()) and "Total Portfolio" in result.answer


def test_pending_requires_clarification(agent):
    result=agent.ask("How many projects are pending?")
    assert result.validation=="needs_clarification" and "does not contain an explicit **Pending** status" in result.answer


def test_completed_percentage(agent):
    result=agent.ask("What percentage of projects are completed?")
    expected=(get_dataframe().status=="Completed").mean()*100
    assert math.isclose(result.table[0]["Value"],expected,rel_tol=1e-4)
    assert "## Calculation" in result.answer


@pytest.mark.parametrize(("question","operation"),[("What is the total project cost?","sum"),("What is the average project cost?","mean")])
def test_financial_answers_include_context(agent,question,operation):
    result=agent.ask(question)
    assert result.plan["operation"]==operation and "PKR" in result.answer
    assert all(label in result.answer for label in ("Average","Minimum","Maximum","## Evidence"))


def test_group_ranking(agent):
    result=agent.ask("Which district has the most projects?")
    expected=get_dataframe().groupby("district").global_id.nunique().sort_values(ascending=False)
    assert result.table[0]["district"]==expected.index[0] and result.table[0]["value"]==expected.iloc[0]


def test_top_ten_expensive_is_numbered(agent):
    result=agent.ask("What are the top 10 most expensive projects?")
    expected=list(get_dataframe().sort_values("cost_m",ascending=False).head(10).global_id)
    assert [row["global_id"] for row in result.table]==expected
    assert "10. **" in result.answer and "PKR" in result.answer


def test_district_comparison(agent):
    result=agent.ask("Compare Kech and Awaran.")
    assert {row["district"] for row in result.table}=={"Kech","Awaran"}
    assert "## Status Breakdown" in result.answer and "## Key Difference" in result.answer


def test_low_progress_list(agent):
    result=agent.ask("Show projects below 20% progress.")
    assert result.table and all(float(row["progress_pct"])<20 for row in result.table)
    assert "Showing" in result.answer and "## Evidence" in result.answer


def test_project_detail_missing_fields_are_explicit(agent):
    result=agent.ask("Tell me about project KAL-0049-P2.")
    assert result.intent=="lookup" and "## Project Details" in result.answer
    assert all(label in result.answer for label in ("Contractor","Start Date","XEN","NITs"))


def test_attention_is_only_attention_route(agent):
    result=agent.ask("Which project needs immediate attention?")
    assert result.intent=="attention_analysis" and "Observed reasons" in result.table[0]
    assert "Missing contractor" in result.answer and "Start date" in result.answer

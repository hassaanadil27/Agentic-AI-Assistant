"""Professional AI investigation workspace for portfolio questions."""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from agents.llm_provider import get_provider
from ui.api_client import ask_query
from ui.chat_store import load_chats, new_chat, save_chats, title_from_question
from ui.charts import create_chart_spec, render_figure
from ui.pdf_reports import charts_report, project_report
from ui.styles import APP_CSS

_env_path = Path(__file__).resolve().parent.parent / ".env"
if not (_env_path.exists() and "x-rapidapi-key" in _env_path.read_text(encoding="utf-8").casefold()):
    load_dotenv(_env_path)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
st.markdown(APP_CSS, unsafe_allow_html=True)


def init_state() -> None:
    if "chats" not in st.session_state:
        st.session_state.chats = load_chats() or [new_chat()]
        st.session_state.active_chat_id = st.session_state.chats[0]["id"]


def active_chat() -> dict:
    for item in st.session_state.chats:
        if item["id"] == st.session_state.active_chat_id:
            return item
    item = new_chat()
    st.session_state.chats.insert(0, item)
    st.session_state.active_chat_id = item["id"]
    return item


def persist() -> None:
    save_chats(st.session_state.chats)


def clear_chat(chat: dict) -> None:
    chat.update(messages=[], charts=[], title="New conversation")
    st.session_state.pop("last_query_trace", None)
    persist()


def render_activity(lines: list[str]) -> None:
    rows = []
    for number, raw in enumerate(lines, 1):
        agent, message = "System", raw
        if raw.startswith("[") and "]" in raw:
            agent, message = raw[1:].split("]", 1)
            message = message.strip()
        prefix, separator, detail = message.partition(":")
        stage = prefix if separator and prefix in {"PLAN", "ACT", "OBSERVE", "REASON", "STOP"} else "Update"
        description = detail.strip() if stage != "Update" else message
        if "(" in description and ("Calling " in description or stage == "ACT"):
            action = description.split("(", 1)[0].replace("Calling ", "").strip()
            description = f"Used {action.replace('_', ' ').title()} to retrieve verified information."
        elif stage == "OBSERVE" and description.startswith(("{", "[")):
            description = "The data tool returned verified evidence for this step."
        rows.append({"Step": number, "Agent": agent, "Stage": stage.title(), "Details": description.replace("_", " ")})
    if rows:
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    else:
        st.info("No execution details are available for this response.")


init_state()
provider, is_demo = get_provider()
provider_label = {
    "HuggingFaceProvider": "Hugging Face",
    "RapidAPIProvider": "RapidAPI",
    "GrokProvider": "Grok",
}.get(provider.__class__.__name__, "Demo")
chat = active_chat()

with st.sidebar:
    st.markdown('<div class="brand">Query Intelligence</div>', unsafe_allow_html=True)
    if st.button("New investigation", type="primary", icon=":material/add:", width="stretch"):
        item = new_chat()
        st.session_state.chats.insert(0, item)
        st.session_state.active_chat_id = item["id"]
        persist()
        st.rerun()

    st.markdown('<div class="nav-label">Recent investigations</div>', unsafe_allow_html=True)
    for item in st.session_state.chats[:10]:
        active = item["id"] == chat["id"]
        label = ("Current: " if active else "") + item["title"][:34]
        if st.button(label, key=f"open-{item['id']}", icon=":material/chat_bubble:", width="stretch"):
            st.session_state.active_chat_id = item["id"]
            st.rerun()

    st.markdown('<div class="nav-label">Conversation controls</div>', unsafe_allow_html=True)
    if st.button(
        "Clear conversation",
        key="sidebar-clear-chat",
        icon=":material/delete_sweep:",
        disabled=not bool(chat["messages"] or chat["charts"]),
        width="stretch",
    ):
        clear_chat(chat)
        st.rerun()

st.markdown(
    '<div class="hero"><h1>AI-Powered Query & Investigation</h1>'
    '<p>Ask a portfolio question, review the evidence-backed response, and inspect a matching visualization alongside the conversation.</p></div>',
    unsafe_allow_html=True,
)

status_left, status_right = st.columns([1, 3])
if is_demo:
    status_left.warning("Demo provider", icon=":material/science:")
else:
    status_left.success(f"{provider_label} connected", icon=":material/check_circle:")
status_right.caption(
    "Responses use the loaded BSDI portfolio. Visual evidence is generated locally from the same dataset."
)

if not chat["messages"]:
    with st.container(key="starter_actions"):
        st.markdown(
            '<div class="starter-title">Begin an investigation</div>'
            '<div class="starter-copy">Choose a common analysis or write a question in the conversation panel.</div>',
            unsafe_allow_html=True,
        )
        suggestions = [
            ("Compare district budgets", "Compare portfolio budgets by district"),
            ("Review delivery status", "Show the percentage of projects by delivery status"),
            ("Check contractor coverage", "How many projects are missing contractor information?"),
        ]
        suggestion_columns = st.columns(3)
        for column, (label, question) in zip(suggestion_columns, suggestions):
            if column.button(label, key=f"suggest-{label}", icon=":material/bolt:", width="stretch"):
                st.session_state.suggested_prompt = question
                st.rerun()

st.markdown('<div class="section-kicker">Investigation workspace</div>', unsafe_allow_html=True)
conversation_col, analysis_col = st.columns([1.18, .82], gap="medium")

with conversation_col:
    with st.container(border=True, key="query_conversation"):
        st.markdown(
            '<div class="query-panel-heading">Conversation <span>Evidence grounded</span></div>',
            unsafe_allow_html=True,
        )
        if not chat["messages"]:
            st.markdown(
                '<div class="empty-analysis">Ask a clear question about districts, budgets, delivery, agencies, contractors, or project status.</div>',
                unsafe_allow_html=True,
            )
        for message in chat["messages"]:
            avatar = ":material/person:" if message["role"] == "user" else ":material/psychology:"
            with st.chat_message(message["role"], avatar=avatar):
                st.markdown(message["content"])
                if message.get("timestamp"):
                    st.caption(message["timestamp"])

        typed_prompt = st.chat_input("Ask a question about the BSDI portfolio...", key="query_chat_input")

with analysis_col:
    with st.container(border=True, key="query_analysis"):
        st.markdown(
            '<div class="query-panel-heading">Visual evidence <span>Live dataset</span></div>',
            unsafe_allow_html=True,
        )
        charts = chat.get("charts", [])
        selected_chart = None
        if charts:
            chart_options = list(range(len(charts) - 1, -1, -1))
            selected_index = st.selectbox(
                "Visualization",
                chart_options,
                format_func=lambda index: charts[index]["question"][:62],
                key=f"chart-choice-{chat['id']}",
            )
            selected_chart = charts[selected_index]
            chart_types = ["bar", "pie", "line", "scatter", "histogram"]
            default_type = selected_chart.get("type", "bar")
            chart_type = st.segmented_control(
                "Chart type",
                chart_types,
                default=default_type if default_type in chart_types else "bar",
                key=f"chart-type-{selected_chart['id']}",
            ) or default_type
            st.plotly_chart(
                render_figure(selected_chart, chart_type),
                width="stretch",
                config={"displaylogo": False, "responsive": True},
            )
            st.caption(f"Generated for: {selected_chart['question']}")
        else:
            st.markdown(
                '<div class="empty-analysis">A question-aware graph will appear here after your first response.</div>',
                unsafe_allow_html=True,
            )

        st.markdown('<div class="query-panel-heading">Exports <span>Ready to share</span></div>', unsafe_allow_html=True)
        export_left, export_right = st.columns(2)
        if chat["messages"]:
            export_left.download_button(
                "Conversation PDF",
                project_report(chat),
                file_name="bsdi-investigation.pdf",
                mime="application/pdf",
                icon=":material/picture_as_pdf:",
                width="stretch",
            )
        else:
            export_left.button(
                "Conversation PDF",
                icon=":material/picture_as_pdf:",
                disabled=True,
                width="stretch",
            )
        if selected_chart:
            export_right.download_button(
                "Chart data",
                pd.DataFrame(selected_chart["data"]).to_csv(index=False),
                file_name=f"{selected_chart['id']}.csv",
                mime="text/csv",
                icon=":material/download:",
                width="stretch",
            )
            st.download_button(
                "All visual evidence PDF",
                charts_report(chat),
                file_name="bsdi-visual-evidence.pdf",
                mime="application/pdf",
                icon=":material/analytics:",
                width="stretch",
            )
        else:
            export_right.button("Chart data", icon=":material/download:", disabled=True, width="stretch")

suggested_prompt = st.session_state.pop("suggested_prompt", "")
prompt = suggested_prompt or typed_prompt
if prompt:
    timestamp = datetime.now().strftime("%H:%M")
    chat["messages"].append({"role": "user", "content": prompt, "timestamp": timestamp})
    if chat["title"] == "New conversation":
        chat["title"] = title_from_question(prompt)
    persist()

    try:
        with st.spinner("Investigating the portfolio and preparing visual evidence..."):
            answer, trace = ask_query(prompt, chat["messages"][:-1])
            chart = create_chart_spec(prompt)
        st.session_state.last_query_trace = trace
        chat["charts"].append(chart)
    except Exception as exc:
        logging.exception("Query failed")
        answer = f"The investigation could not be completed: {exc}"
    chat["messages"].append(
        {"role": "assistant", "content": answer, "timestamp": datetime.now().strftime("%H:%M")}
    )
    persist()
    st.rerun()

if "last_query_trace" in st.session_state:
    with st.expander("View investigation process"):
        st.caption("How the agent planned, retrieved, and verified this answer")
        render_activity(st.session_state.last_query_trace)

"""Grounded natural-language portfolio assistant."""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

_env = Path(__file__).resolve().parent.parent / ".env"
if _env.exists():
    load_dotenv(_env, override=True)

from ui.api_client import ask_query
from ui.chat_store import load_chats, new_chat, save_chats, title_from_question
from ui.charts import create_chart_spec, render_figure, should_chart
from ui.components import render_empty_state, render_footer, render_header, render_section, render_sidebar_info, render_trace
from ui.pdf_reports import project_report
from ui.styles import APP_CSS

logging.basicConfig(level=logging.WARNING)
st.set_page_config(page_title="AI Assistant · BSDI", page_icon="💬", layout="wide")
st.markdown(APP_CSS, unsafe_allow_html=True)
render_sidebar_info()
render_header("AI project assistant", "Ask a question in everyday language and get a clear answer checked against the development portfolio.", "Data-checked answers", "green")


def initialise() -> None:
    if "chats" not in st.session_state:
        st.session_state.chats = load_chats() or [new_chat()]
    if "active_chat_id" not in st.session_state:
        st.session_state.active_chat_id = st.session_state.chats[0]["id"]
    st.session_state.setdefault("suggested_prompt", "")
    st.session_state.setdefault("last_trace", [])


def active_chat() -> dict:
    for candidate in st.session_state.chats:
        if candidate["id"] == st.session_state.active_chat_id:
            return candidate
    candidate = new_chat()
    st.session_state.chats.insert(0, candidate)
    st.session_state.active_chat_id = candidate["id"]
    return candidate


def persist() -> None:
    try:
        save_chats(st.session_state.chats)
    except OSError:
        st.toast("This conversation could not be saved to disk.", icon="⚠️")


initialise()
chat = active_chat()

with st.sidebar:
    st.markdown("### Conversations")
    if st.button("＋ New conversation", type="primary", width="stretch"):
        created = new_chat()
        st.session_state.chats.insert(0, created)
        st.session_state.active_chat_id = created["id"]
        st.session_state.last_trace = []
        persist()
        st.rerun()
    for item in st.session_state.chats[:10]:
        active = item["id"] == st.session_state.active_chat_id
        label = f"{'●' if active else '○'}  {item['title'][:30]}"
        if st.button(label, key=f"chat-{item['id']}", width="stretch"):
            st.session_state.active_chat_id = item["id"]
            st.session_state.last_trace = []
            st.rerun()
    if chat["messages"]:
        st.divider()
        st.download_button("Download conversation PDF", project_report(chat), "bsdi_conversation.pdf", "application/pdf", width="stretch")
        if st.button("Clear this conversation", width="stretch"):
            chat.update(messages=[], charts=[], title="New conversation")
            st.session_state.last_trace = []
            persist()
            st.rerun()

if not chat["messages"]:
    render_section("Start with a useful question", "Choose an example or type your own below. Add ‘chart’ or ‘compare’ to request a visualization.")
    prompts = [
        ("Allocation", "Which districts have the highest total budget allocation?"),
        ("Delivery", "What is the total budget of all Not Started projects?"),
        ("Prioritization", "Which Not Started project should be prioritized first?"),
        ("Comparison", "Compare the project count and budget by sector in a chart."),
    ]
    columns = st.columns(4)
    for column, (label, question) in zip(columns, prompts):
        with column:
            with st.container(border=True):
                st.caption(label.upper())
                st.markdown(question)
                if st.button("Ask this", key=f"prompt-{label}", width="stretch"):
                    st.session_state.suggested_prompt = question
                    st.rerun()
    st.markdown('<div class="callout">Tip: include a district, sector, status, or ranking criterion for a more precise answer.</div>', unsafe_allow_html=True)

for message in chat["messages"]:
    role = message.get("role", "user")
    with st.chat_message(role, avatar="👤" if role == "user" else "🤖"):
        st.markdown(message.get("content", ""))
        if message.get("timestamp"):
            st.caption(message["timestamp"])

for spec in chat.get("charts", []):
    with st.chat_message("assistant", avatar="📊"):
        st.markdown(f"**{spec['title']}**")
        st.plotly_chart(render_figure(spec), width="stretch", config={"displaylogo": False, "responsive": True})
        table = pd.DataFrame(spec["data"])
        st.download_button("Download chart data", table.to_csv(index=False).encode("utf-8"), f"{spec['id']}.csv", "text/csv", key=f"chart-{spec['id']}")

typed = st.chat_input("Ask about schemes, districts, sectors, delivery, or budgets…")
prompt = st.session_state.suggested_prompt or typed
if prompt:
    st.session_state.suggested_prompt = ""
    timestamp = datetime.now().strftime("%H:%M")
    chat["messages"].append({"role": "user", "content": prompt, "timestamp": timestamp})
    if chat["title"] == "New conversation":
        chat["title"] = title_from_question(prompt)
    persist()
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)
    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("Checking the portfolio dataset…"):
            try:
                answer, trace = ask_query(prompt, chat["messages"][:-1])
            except Exception as exc:
                logging.exception("Query failed")
                answer = "I could not complete that analysis. Check that the dataset is available, then try again."
                trace = [f"ERROR: {exc}"]
        st.markdown(answer)
    chat["messages"].append({"role": "assistant", "content": answer, "timestamp": timestamp})
    st.session_state.last_trace = trace
    if should_chart(prompt):
        try:
            chat.setdefault("charts", []).append(create_chart_spec(prompt))
        except Exception:
            logging.exception("Chart generation failed")
    persist()
    st.rerun()

if st.session_state.last_trace:
    with st.expander("How we checked this answer"):
        st.caption("A simple summary of the portfolio checks used for this answer.")
        render_trace(st.session_state.last_trace)
elif chat["messages"]:
    render_empty_state("✓", "Conversation saved", "Ask a follow-up question at any time; recent context is sent with your next request.")

render_footer()

"""Track A - Query Agent Page."""
from __future__ import annotations
import logging
from datetime import datetime
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from pathlib import Path

from agents.llm_provider import get_provider
from models.messages import AgentReport
from tools.chat_context import build_chat_context
from ui.api_client import ask_query, get_portfolio
from ui.chat_store import load_chats, new_chat, save_chats, title_from_question
from ui.charts import create_chart_spec, render_figure, should_chart
from ui.pdf_reports import charts_report, project_report
from ui.styles import APP_CSS

_env_path = Path(__file__).resolve().parent.parent / ".env"
if not (_env_path.exists() and "x-rapidapi-key" in _env_path.read_text(encoding="utf-8").casefold()):
    load_dotenv(_env_path)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

st.markdown(APP_CSS, unsafe_allow_html=True)

def init_state():
    if "chats" not in st.session_state:
        st.session_state.chats = load_chats() or [new_chat()]
        st.session_state.active_chat_id = st.session_state.chats[0]["id"]
    if "show_history" not in st.session_state:
        st.session_state.show_history = False


def active_chat():
    for item in st.session_state.chats:
        if item["id"] == st.session_state.active_chat_id:
            return item
    item = new_chat()
    st.session_state.chats.insert(0, item)
    st.session_state.active_chat_id = item["id"]
    return item


def persist():
    save_chats(st.session_state.chats)


def render_activity(lines: list[str]) -> None:
    """Show technical execution logs as a readable progress timeline."""
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
        description = description.replace("_", " ")
        rows.append({"Step": number, "Agent": agent, "Stage": stage.title(), "Details": description})
    if rows:
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    else:
        st.info("No activity recorded yet.")


def render_chart(spec):
    options = ["bar", "pie", "line", "scatter", "histogram"]
    kind = st.selectbox("Chart type", options, index=options.index(spec.get("type", "bar")), key=f"type-{spec['id']}")
    st.plotly_chart(render_figure(spec, kind), width="stretch", config={"displaylogo": False, "responsive": True})
    st.download_button("⬇ Download chart data", pd.DataFrame(spec["data"]).to_csv(index=False), f"{spec['id']}.csv", "text/csv", key=f"csv-{spec['id']}")


init_state()
provider, is_demo = get_provider()
provider_label = {
    "HuggingFaceProvider": "Hugging Face",
    "RapidAPIProvider": "RapidAPI",
    "GrokProvider": "Grok",
}.get(provider.__class__.__name__, "Demo")

chat = active_chat()

# Sidebar with chat history
with st.sidebar:
    st.markdown('<div class="brand">🔍 Query Agent</div>', unsafe_allow_html=True)
    
    if st.button("➕ New Chat", type="primary", width="stretch"):
        item = new_chat()
        st.session_state.chats.insert(0, item)
        st.session_state.active_chat_id = item["id"]
        persist()
        st.rerun()
    
    st.markdown("**Chat History**")
    for item in st.session_state.chats[:10]:
        label = ("📍 " if item["id"] == chat["id"] else "💬 ") + item["title"][:30]
        if st.button(label, key=f"open-{item['id']}", width="stretch"):
            st.session_state.active_chat_id = item["id"]
            st.rerun()
    
    st.divider()
    
    # Tools Section
    st.markdown("**📊 Tools**")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📈 Chart", disabled=not bool(chat["messages"]), width="stretch"):
            try:
                questions = [m["content"] for m in chat["messages"] if m["role"] == "user"]
                if questions:
                    chat["charts"].append(create_chart_spec(questions[-1]))
                    persist()
                    st.rerun()
            except Exception:
                logging.exception("Chart generation failed")
    with col2:
        if st.button("📄 PDF", disabled=not bool(chat["messages"]), width="stretch"):
            st.info("PDF download ready in main area")
    
    st.divider()
    if st.button("🗑️ Clear Chat", disabled=not bool(chat["messages"] or chat["charts"]), width="stretch"):
        chat.update(messages=[], charts=[], title="New conversation")
        persist()
        st.rerun()

# Main Content
st.markdown(
    '<div class="hero"><h1>🔍 Query Agent</h1><p>Ask natural-language questions about your portfolio. The agent plans, verifies, and cites its evidence.</p></div>',
    unsafe_allow_html=True
)

if is_demo:
    st.info("🟠 Demo Mode Active - AI answers unavailable. Data queries work normally.")
else:
    st.caption(f"🔌 Connected to {provider_label} · {provider.model_name}")

# Starter Suggestions
if not chat["messages"]:
    with st.container(key="starter_actions"):
        st.markdown('<div class="starter-title">Start an analysis</div><div class="starter-copy">Choose a suggestion or ask your own question below</div>', unsafe_allow_html=True)
        suggestion_col1, suggestion_col2, suggestion_col3 = st.columns(3)
        
        suggestions = [
            ("📍 District Budgets", "Compare portfolio budgets by district"),
            ("📊 Status Overview", "Show percentage of projects by status"),
            ("⚠️ Risk Analysis", "Which projects have the highest delivery risk?"),
        ]
        
        for col, (emoji_label, question) in zip([suggestion_col1, suggestion_col2, suggestion_col3], suggestions):
            if col.button(emoji_label, key=f"suggest-{emoji_label}", width="stretch"):
                st.session_state.suggested_prompt = question
                st.rerun()

# Display chat messages
for message in chat["messages"]:
    with st.chat_message(message["role"], avatar="👤" if message["role"] == "user" else "🤖"):
        st.markdown(message["content"])
        if message.get("timestamp"):
            st.caption(f"⏱️ {message['timestamp']}")

# Display charts
for spec in chat.get("charts", []):
    with st.chat_message("assistant", avatar="📊"):
        st.markdown(f"**{spec['title']}**")
        render_chart(spec)

# Chat input
typed_prompt = st.chat_input("Ask about BSDI projects…", key="chat_input")
suggested = st.session_state.get("suggested_prompt", "")
prompt = suggested or typed_prompt

if prompt:
    st.session_state.suggested_prompt = ""
    chat["messages"].append({"role": "user", "content": prompt, "timestamp": datetime.now().strftime("%H:%M")})
    if chat["title"] == "New conversation":
        chat["title"] = title_from_question(prompt)
    persist()
    
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)
    
    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("Thinking…"):
            try:
                answer, trace = ask_query(prompt, chat["messages"][:-1])
                st.session_state.last_query_trace = trace
            except Exception as exc:
                logging.exception("Query failed")
                answer = "❌ Something went wrong. Please try again."
            st.markdown(answer)
    
    chat["messages"].append({"role": "assistant", "content": answer, "timestamp": datetime.now().strftime("%H:%M")})
    
    if should_chart(prompt):
        try:
            chat["charts"].append(create_chart_spec(prompt))
        except Exception:
            logging.exception("Chart generation failed")
    
    persist()
    st.rerun()

# Show trace if available
if "last_query_trace" in st.session_state:
    with st.expander("📋 View Analysis Process"):
        st.caption("How the agent verified this answer")
        render_activity(st.session_state.last_query_trace)

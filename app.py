"""BSDI Project AI Agent — chat-first Streamlit application."""
from __future__ import annotations

import logging
from pathlib import Path
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from agents.coordinator_agent import CoordinatorAgent
from agents.llm_provider import DemoProvider, get_provider
from orchestration.state import save_run_log
from tools.chat_context import build_chat_context
from tools.data_loader import load_projects
from tools.data_quality_tools import get_data_quality_report
from tools.finance_tools import category_statistics, district_statistics
from ui.chat_store import load_chats, new_chat, save_chats, title_from_question
from ui.charts import create_chart_spec, render_figure, should_chart
from ui.pdf_reports import charts_report, project_report
from ui.styles import APP_CSS

_env_path = Path(__file__).resolve().parent / ".env"
# RapidAPI's copied Python example is not dotenv syntax. The provider can
# safely extract its key, while normal key=value files still use dotenv.
if not (_env_path.exists() and "x-rapidapi-key" in _env_path.read_text(encoding="utf-8").casefold()):
    load_dotenv(_env_path)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
st.set_page_config(page_title="BSDI Project AI Agent", page_icon="📊", layout="wide")
st.markdown(APP_CSS, unsafe_allow_html=True)


def init_state():
    if "chats" not in st.session_state:
        st.session_state.chats = load_chats() or [new_chat()]
        st.session_state.active_chat_id = st.session_state.chats[0]["id"]


def active_chat():
    for item in st.session_state.chats:
        if item["id"] == st.session_state.active_chat_id:
            return item
    item = new_chat(); st.session_state.chats.insert(0, item)
    st.session_state.active_chat_id = item["id"]
    return item


def persist():
    save_chats(st.session_state.chats)


def sidebar(chat):
    with st.sidebar:
        st.markdown('<div class="brand">BSDI Project <span class="brand-dot">AI Agent</span></div>', unsafe_allow_html=True)
        page = st.radio("Workspace", ["💬 AI Chat", "📋 Review Board"], label_visibility="collapsed")
        if st.button("＋ New Chat", type="primary"):
            item = new_chat(); st.session_state.chats.insert(0, item)
            st.session_state.active_chat_id = item["id"]; persist(); st.rerun()
        st.caption("CHAT HISTORY")
        for item in st.session_state.chats:
            label = ("● " if item["id"] == chat["id"] else "") + item["title"]
            if st.button(label, key=f"open-{item['id']}"):
                st.session_state.active_chat_id = item["id"]; st.rerun()
        st.divider(); st.caption("PROJECT TOOLS")
        questions = [m["content"] for m in chat["messages"] if m["role"] == "user"]
        if st.button("📊 Generate Chart", disabled=not questions):
            chat["charts"].append(create_chart_spec(questions[-1])); persist(); st.rerun()
        st.download_button("📄 Download Project Details", project_report(chat), "bsdi_project_report.pdf", "application/pdf", width="stretch")
        st.download_button("📈 Download Charts PDF", charts_report(chat), "bsdi_charts_report.pdf", "application/pdf", width="stretch")
        if st.button("🗑 Clear Current Chat", disabled=not chat["messages"] and not chat["charts"]):
            chat.update(messages=[], charts=[], title="New conversation"); persist(); st.rerun()
        st.caption(f"{len(chat['messages'])} messages · {len(chat['charts'])} charts")
    return page


def render_chart(spec):
    options = ["bar", "pie", "line", "scatter", "histogram"]
    kind = st.selectbox("Chart type", options, index=options.index(spec.get("type", "bar")), key=f"type-{spec['id']}")
    st.plotly_chart(render_figure(spec, kind), width="stretch", config={"displaylogo": False, "responsive": True, "toImageButtonOptions": {"filename": spec["title"]}})
    st.download_button("⬇ Download chart data", pd.DataFrame(spec["data"]).to_csv(index=False), f"{spec['id']}.csv", "text/csv", key=f"csv-{spec['id']}")


def chat_page(chat, provider, is_demo, provider_label):
    st.markdown('<div class="hero"><h1>BSDI Project AI Agent</h1><p>Ask about 4,083 development projects, compare districts, and create evidence-based visualisations.</p></div>', unsafe_allow_html=True)
    if is_demo:
        st.info("Demo Mode is active. Data analysis remains available; connect a supported API token for conversational AI.")
    else:
        st.caption(f"Connected to {provider_label} · {provider.model_name}")
    if not chat["messages"]:
        st.markdown("#### What would you like to analyse?")
        st.caption("Try: “Compare portfolio budgets by district” or “Show the percentage of projects by status.”")
    for message in chat["messages"]:
        with st.chat_message(message["role"], avatar="🧑‍💼" if message["role"] == "user" else "📊"):
            st.markdown(message["content"]); st.caption(message.get("timestamp", ""))
    for spec in chat.get("charts", []):
        with st.chat_message("assistant", avatar="📊"):
            st.markdown(f"**{spec['title']}**"); render_chart(spec)

    prompt = st.chat_input("Ask about BSDI projects…", disabled=is_demo)
    if prompt:
        from datetime import datetime
        chat["messages"].append({"role": "user", "content": prompt, "timestamp": datetime.now().strftime("%H:%M")})
        if chat["title"] == "New conversation": chat["title"] = title_from_question(prompt)
        persist()
        with st.chat_message("user", avatar="🧑‍💼"): st.markdown(prompt)
        with st.chat_message("assistant", avatar="📊"):
            with st.spinner("AI is thinking…"):
                try:
                    context = build_chat_context(prompt)
                    response = provider.complete(
                        "You are the BSDI Project AI Agent. Answer only from the authoritative PROJECT DATA CONTEXT. "
                        "Never invent values. Costs are PKR millions. If a project is absent, request its Global ID. "
                        "Be concise and analytical.\n\nPROJECT DATA CONTEXT:\n" + context,
                        chat["messages"],
                    )
                    answer = response.text
                except Exception as exc:
                    logging.exception("Chat request failed")
                    answer = "Something went wrong while processing your request. Please try again."
                st.markdown(answer)
        chat["messages"].append({"role": "assistant", "content": answer, "timestamp": datetime.now().strftime("%H:%M")})
        if should_chart(prompt):
            try: chat["charts"].append(create_chart_spec(prompt))
            except Exception: logging.exception("Unable to generate chart")
        persist(); st.rerun()


def review_page(provider, is_demo):
    st.markdown('<div class="hero"><h1>Multi-Agent Review Board</h1><p>Finance, delivery, and equity specialists prioritise projects within a controlled funding envelope.</p></div>', unsafe_allow_html=True)
    with st.spinner("Loading portfolio…"): meta = load_projects()
    cols = st.columns(4)
    for col, label, value in zip(cols, ["Total Projects", "Portfolio Value", "Districts", "Categories"], [f"{meta.total_projects:,}", f"PKR {meta.total_portfolio_m:,.1f}M", meta.districts, meta.categories]): col.metric(label, value)
    tabs = st.tabs(["Portfolio", "Data Quality", "Run Review"])
    with tabs[0]:
        districts = pd.DataFrame([d.model_dump() for d in district_statistics()]).sort_values("total_budget_m", ascending=False).head(15)
        categories = pd.DataFrame([c.model_dump() for c in category_statistics()]).sort_values("total_budget_m", ascending=False)
        a, b = st.columns(2); a.bar_chart(districts.set_index("district")["total_budget_m"]); b.bar_chart(categories.set_index("category")["total_budget_m"])
    with tabs[1]: st.json(get_data_quality_report().model_dump(), expanded=False)
    with tabs[2]:
        budget = st.number_input("Funding envelope (PKR Million)", 100.0, 20000.0, 2000.0, 100.0)
        if st.button("🚀 Run Multi-Agent Review", type="primary"):
            with st.spinner("Agents are analysing finance, delivery, and equity…"):
                try: report, activity, specialists = CoordinatorAgent(provider, is_demo).run_review(budget_cap_m=budget)
                except Exception as exc:
                    st.info(f"Live LLM unavailable ({exc}). Review completed with deterministic analysis.")
                    report, activity, specialists = CoordinatorAgent(DemoProvider(), True).run_review(budget_cap_m=budget)
                path = save_run_log(report, activity, specialists)
                st.session_state.review_result = (report, activity, specialists, str(path))
        if "review_result" in st.session_state:
            report, activity, specialists, path = st.session_state.review_result
            st.success(f"Review complete · {len(report.recommended_projects)} projects selected")
            c = st.columns(3); c[0].metric("Available", f"PKR {report.budget_available_m:,.1f}M"); c[1].metric("Recommended", f"PKR {report.total_recommended_m:,.2f}M"); c[2].metric("Remaining", f"PKR {report.remaining_budget_m:,.2f}M")
            rec = pd.DataFrame([r.model_dump() for r in report.recommended_projects])
            st.dataframe(rec, width="stretch", hide_index=True)
            st.download_button("Download recommendations", rec.to_csv(index=False), "pmts_recommendations.csv", "text/csv")
            with st.expander("Agent activity"): st.code("\n".join(activity))


init_state()
provider, is_demo = get_provider()
provider_label = {
    "HuggingFaceProvider": "Hugging Face",
    "RapidAPIProvider": "RapidAPI",
    "GrokProvider": "Grok",
}.get(provider.__class__.__name__, "Demo")
chat = active_chat(); page = sidebar(chat)
chat_page(chat, provider, is_demo, provider_label) if page == "💬 AI Chat" else review_page(provider, is_demo)

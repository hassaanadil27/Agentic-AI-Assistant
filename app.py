"""BSDI Project AI Agent — chat-first Streamlit application."""
from __future__ import annotations

import logging
from pathlib import Path
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from agents.coordinator_agent import CoordinatorAgent
from agents.llm_provider import DemoProvider, get_provider
from agents.query_agent import QueryAgent
from agents.audit_agent import AuditAgent, AuditResult
from models.messages import AgentReport, FinalReport
from orchestration.state import load_audit_state, load_latest_run, save_audit_state, save_run_log
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
        requested_chat = st.query_params.get("chat")
        available_ids = {item["id"] for item in st.session_state.chats}
        st.session_state.active_chat_id = requested_chat if requested_chat in available_ids else st.session_state.chats[0]["id"]
    if "audit_result" not in st.session_state:
        saved_audit = load_audit_state()
        if saved_audit and isinstance(saved_audit.get("result"), dict):
            st.session_state.audit_result = AuditResult(**saved_audit["result"])
            st.session_state.audit_goal = saved_audit.get("goal", "")
    if "review_result" not in st.session_state:
        saved_review = load_latest_run()
        if saved_review:
            report = FinalReport.model_validate(saved_review["final_report"])
            specialists = {name: AgentReport.model_validate(value) for name, value in saved_review.get("specialist_reports", {}).items()}
            st.session_state.review_result = (report, saved_review.get("activity_log", []), specialists, "saved run")


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
        pages = ["Track A · Query", "Track B · Audit", "Track C · Review Board"]
        view_index = {"query": 0, "audit": 1, "review": 2}.get(st.query_params.get("view", "query"), 0)
        if "workspace" not in st.session_state:
            st.session_state.workspace = pages[view_index]

        def sync_workspace():
            selected = pages.index(st.session_state.workspace)
            st.query_params["view"] = ["query", "audit", "review"][selected]
            st.query_params["chat"] = st.session_state.active_chat_id

        page = st.radio("Workspace", pages, key="workspace", on_change=sync_workspace, label_visibility="collapsed")
        if st.button("＋ New Chat", type="primary"):
            item = new_chat(); st.session_state.chats.insert(0, item)
            st.session_state.active_chat_id = item["id"]; st.query_params["chat"] = item["id"]; persist(); st.rerun()
        st.caption("CHAT HISTORY")
        for item in st.session_state.chats:
            label = ("● " if item["id"] == chat["id"] else "") + item["title"]
            if st.button(label, key=f"open-{item['id']}"):
                st.session_state.active_chat_id = item["id"]; st.query_params["chat"] = item["id"]; st.rerun()
        st.divider()
        questions = [m["content"] for m in chat["messages"] if m["role"] == "user"]
        has_content = bool(chat["messages"] or chat["charts"])
        with st.container(key="project_tools"):
            st.markdown(
                '<div class="tools-heading"><span class="tools-icon">✦</span>'
                '<div><strong>Project Tools</strong><small>Create and export your analysis</small></div></div>',
                unsafe_allow_html=True,
            )
            if st.button("📊  Generate Chart", type="primary", disabled=not questions, key="project_generate", help="Ask a question first to generate a chart"):
                chat["charts"].append(create_chart_spec(questions[-1])); persist(); st.rerun()
            st.download_button("📄  Download Project Details", project_report(chat), "bsdi_project_report.pdf", "application/pdf", width="stretch", disabled=not chat["messages"], key="project_details")
            st.download_button("📈  Download Charts PDF", charts_report(chat), "bsdi_charts_report.pdf", "application/pdf", width="stretch", disabled=not chat["charts"], key="project_charts")
            if st.button("🗑️  Clear Current Chat", disabled=not has_content, key="project_clear"):
                chat.update(messages=[], charts=[], title="New conversation"); persist(); st.rerun()
            st.markdown(
                f'<div class="tools-status"><span>{len(chat["messages"])} messages</span>'
                f'<span>{len(chat["charts"])} charts</span></div>',
                unsafe_allow_html=True,
            )
    return page


def render_chart(spec):
    options = ["bar", "pie", "line", "scatter", "histogram"]
    kind = st.selectbox("Chart type", options, index=options.index(spec.get("type", "bar")), key=f"type-{spec['id']}")
    st.plotly_chart(render_figure(spec, kind), width="stretch", config={"displaylogo": False, "responsive": True, "toImageButtonOptions": {"filename": spec["title"]}})
    st.download_button("⬇ Download chart data", pd.DataFrame(spec["data"]).to_csv(index=False), f"{spec['id']}.csv", "text/csv", key=f"csv-{spec['id']}")


def chat_page(chat, provider, is_demo, provider_label):
    st.markdown('<div class="hero"><h1>Track A · Query Agent</h1><p>Ask grounded natural-language questions; the agent plans, calls query tools, observes results, and cites its evidence.</p></div>', unsafe_allow_html=True)
    if is_demo:
        st.info("Demo Mode is active. Data analysis remains available; connect a supported API token for conversational AI.")
    else:
        st.caption(f"Connected to {provider_label} · {provider.model_name}")
    suggested_prompt = None
    if not chat["messages"]:
        with st.container(key="starter_actions"):
            st.markdown('<div class="starter-title">Start an analysis</div><div class="starter-copy">Choose a quick action or write your own question below.</div>', unsafe_allow_html=True)
            suggestions = [
                ("📍 District budgets", "Compare portfolio budgets by district"),
                ("📊 Project status", "Show the percentage of projects by status"),
                ("⚠️ Delivery risks", "Which projects have the highest delivery risk?"),
            ]
            for col, (label, question) in zip(st.columns(3), suggestions):
                if col.button(label, key=f"suggest-{label}", width="stretch"):
                    suggested_prompt = question
    for message in chat["messages"]:
        with st.chat_message(message["role"], avatar="🧑‍💼" if message["role"] == "user" else "📊"):
            st.markdown(message["content"]); st.caption(message.get("timestamp", ""))
    for spec in chat.get("charts", []):
        with st.chat_message("assistant", avatar="📊"):
            st.markdown(f"**{spec['title']}**"); render_chart(spec)

    typed_prompt = st.chat_input("Ask about BSDI projects…")
    prompt = suggested_prompt or typed_prompt
    if prompt:
        from datetime import datetime
        chat["messages"].append({"role": "user", "content": prompt, "timestamp": datetime.now().strftime("%H:%M")})
        if chat["title"] == "New conversation": chat["title"] = title_from_question(prompt)
        persist()
        with st.chat_message("user", avatar="🧑‍💼"): st.markdown(prompt)
        with st.chat_message("assistant", avatar="📊"):
            with st.spinner("AI is thinking…"):
                try:
                    result = QueryAgent(provider).ask(prompt, chat["messages"][:-1])
                    answer = result.answer
                    st.session_state.last_query_trace = result.trace
                except Exception as exc:
                    logging.exception("Chat request failed")
                    answer = "Something went wrong while processing your request. Please try again."
                st.markdown(answer)
        chat["messages"].append({"role": "assistant", "content": answer, "timestamp": datetime.now().strftime("%H:%M")})
        if should_chart(prompt):
            try: chat["charts"].append(create_chart_spec(prompt))
            except Exception: logging.exception("Unable to generate chart")
        persist(); st.rerun()
    if "last_query_trace" in st.session_state:
        with st.expander("Plan · Tool calls · Evidence"):
            st.code("\n".join(st.session_state.last_query_trace))


def audit_page(provider, is_demo):
    st.markdown('<div class="hero"><h1>Track B · Autonomous Audit Agent</h1><p>Give the agent an audit goal. It creates its own check plan, executes independent tools, and prioritises portfolio risks.</p></div>', unsafe_allow_html=True)
    goal = st.text_area("Audit goal", st.session_state.get("audit_goal", "Find the projects most at risk of failing or being mismanaged."))
    if st.button("Run Autonomous Audit", type="primary"):
        with st.spinner("Audit Agent is planning and running checks…"):
            try:
                st.session_state.audit_result = AuditAgent(provider).run(goal)
                st.session_state.audit_goal = goal
                save_audit_state(goal, st.session_state.audit_result)
            except Exception as exc: st.error(f"Audit failed: {exc}")
    if "audit_result" in st.session_state:
        result = st.session_state.audit_result
        st.subheader("Autonomous plan")
        for index, check in enumerate(result.plan, 1): st.write(f"{index}. `{check}`")
        st.subheader("Prioritized audit report"); st.markdown(result.report)
        st.subheader("Structured findings")
        for finding in result.findings:
            with st.expander(f"{finding['check']} · {finding['count']} issue(s)"):
                st.json(finding)
        with st.expander("Plan · Act · Observe trace"):
            st.code("\n".join(result.trace))


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
if page.startswith("Track A"):
    chat_page(chat, provider, is_demo, provider_label)
elif page.startswith("Track B"):
    audit_page(provider, is_demo)
else:
    review_page(provider, is_demo)

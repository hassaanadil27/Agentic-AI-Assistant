"""Reusable, accessible presentation components for every Streamlit page."""
from __future__ import annotations

import html
import json
from pathlib import Path
import streamlit as st

from agents.llm_provider import get_provider

LOGO_PATH = Path(__file__).resolve().parent.parent / "assets" / "bsdi-logo.png"


def safe_text(value: object) -> str:
    return html.escape("" if value is None else str(value))


def render_header(title: str, subtitle: str, badge_text: str = "Python verified", badge_type: str = "green") -> None:
    badge_class = f"badge-{badge_type}" if badge_type in {"green", "blue", "amber", "red", "neutral"} else "badge-blue"
    st.html(
        f"""
        <div class="app-header">
          <div class="app-header__content">
            <div class="app-header__eyebrow">BSDI · Decision intelligence</div>
            <h1>{safe_text(title)}</h1>
            <p>{safe_text(subtitle)}</p>
          </div>
          <div class="app-header__badge"><span class="badge {badge_class}">● {safe_text(badge_text)}</span></div>
        </div>
        """,
    )


def render_stat(title: str, value: str, subtext: str = "", badge: str | None = None, badge_type: str = "blue") -> None:
    badge_html = f'<span class="badge badge-{badge_type}">{safe_text(badge)}</span>' if badge else ""
    st.markdown(
        f"""
        <div class="stat-card">
          <div class="stat-card__top"><span class="stat-label">{safe_text(title)}</span>{badge_html}</div>
          <div class="stat-value">{safe_text(value)}</div>
          <div class="stat-desc">{safe_text(subtext)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section(title: str, subtitle: str = "") -> None:
    st.markdown(
        f"""
        <div class="section-heading">
          <div class="section-heading__row"><span class="section-heading__accent"></span><h2>{safe_text(title)}</h2></div>
          {f'<p>{safe_text(subtitle)}</p>' if subtitle else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_workflow_card(icon: str, title: str, description: str) -> None:
    st.markdown(
        f"""
        <div class="workflow-card">
          <div class="workflow-card__icon">{safe_text(icon)}</div>
          <h3>{safe_text(title)}</h3>
          <p>{safe_text(description)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_track_card(name: str, purpose: str, activity: str, status: str = "Active", tone: str = "blue") -> None:
    """Explain an agent/workflow track in clear, non-technical English."""
    st.markdown(
        f"""
        <div class="track-card track-card--{safe_text(tone)}">
          <div class="track-card__top"><strong>{safe_text(name)}</strong><span>{safe_text(status)}</span></div>
          <p>{safe_text(purpose)}</p>
          <div class="track-card__activity"><b>Current task</b><br>{safe_text(activity)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_callout(text: str) -> None:
    st.markdown(f'<div class="callout">{safe_text(text)}</div>', unsafe_allow_html=True)


def render_empty_state(icon: str, title: str, description: str) -> None:
    st.markdown(
        f'<div class="empty-state"><div class="empty-state__icon">{safe_text(icon)}</div><strong>{safe_text(title)}</strong>{safe_text(description)}</div>',
        unsafe_allow_html=True,
    )


def render_trace(lines: list[str]) -> None:
    """Turn developer tool logs into a short, plain-language verification trail."""
    labels = {"PLAN": "Question understood", "ACT": "Data checked", "OBSERVE": "Check result", "STOP": "Answer verified", "ERROR": "Connection note"}
    tool_labels = {
        "aggregate_projects": "Calculated the matching project total",
        "filter_projects": "Searched the matching project records",
        "group_projects": "Compared the portfolio groups",
        "get_project": "Looked up the project record",
        "rank_funding_candidates": "Compared eligible funding candidates",
    }
    for raw in lines:
        tag, separator, body = str(raw).partition(":")
        if not separator:
            tag, body = "STEP", str(raw)
        tag = tag.strip().upper()
        body = body.strip()
        if "live planner unavailable" in body.casefold() or "api call failed" in body.casefold():
            friendly = "The online AI was unavailable, so the built-in portfolio checker continued safely."
        elif tag == "PLAN":
            friendly = "Your question was understood and the relevant portfolio check was selected."
        elif tag == "ACT":
            tool_name = body.split("(", 1)[0].strip()
            friendly = tool_labels.get(tool_name, "Checked the relevant portfolio records") + "."
        elif tag == "OBSERVE" and body.startswith("{"):
            try:
                data = json.loads(body)
                operation, value, count = data.get("operation"), data.get("value"), data.get("count")
                if operation == "count" and value is not None:
                    friendly = f"Found {int(float(value)):,} matching project(s)."
                elif operation == "total_cost" and value is not None:
                    friendly = f"Calculated a total value of PKR {float(value):,.2f} million across {int(count or 0):,} project(s)."
                elif count is not None:
                    friendly = f"Found {int(count):,} matching record(s)."
                else:
                    friendly = "The requested portfolio data was found."
            except (ValueError, TypeError, json.JSONDecodeError):
                friendly = "The requested portfolio data was found."
        elif tag == "STOP":
            friendly = "The answer was checked against the portfolio data."
        else:
            friendly = body.replace("_", " ")
        st.html(
            f'<div class="trace-step"><span class="trace-step__tag">{safe_text(labels.get(tag, "Verification"))}</span><span class="trace-step__body">{safe_text(friendly)}</span></div>',
        )


def render_sidebar_info() -> None:
    provider, is_demo = get_provider()
    engine_name = {
        "GeminiProvider": "Google Gemini",
    }.get(provider.__class__.__name__, "Local rule engine")
    mode = "Offline demo" if is_demo else "Connected AI"
    dot = "#f4b942" if is_demo else "#5ee0b3"
    if LOGO_PATH.exists():
        st.logo(str(LOGO_PATH), size="large", icon_image=str(LOGO_PATH))
    with st.sidebar:
        st.html(
            f"""
            <div class="sidebar-brand">
              <div class="sidebar-brand__eyebrow">GOVERNMENT PORTFOLIO</div>
              <div class="sidebar-brand__title">BSDI Platform</div>
              <div class="sidebar-brand__copy">Clear, evidence-led development decisions.</div>
            </div>
            """
        )
        navigation = [
            ("app.py", "Home", ":material/home:", "/"),
            ("pages/1_Overview_and_Explorer.py", "Overview & Explorer", ":material/monitoring:", "/Overview_and_Explorer"),
            ("pages/2_AI_Assistant.py", "AI Assistant", ":material/chat:", "/AI_Assistant"),
            ("pages/3_Risk_Audit.py", "Risk Audit", ":material/policy:", "/Risk_Audit"),
            ("pages/4_Budget_Review_Board.py", "Budget Review Board", ":material/groups:", "/Budget_Review_Board"),
        ]
        for path, label, icon, fallback_url in navigation:
            try:
                st.page_link(path, label=label, icon=icon, width="stretch")
            except KeyError:
                # Isolated page smoke tests do not build Streamlit's multipage registry.
                st.markdown(f'<a class="sidebar-fallback-link" href="{fallback_url}" target="_self">{safe_text(label)}</a>', unsafe_allow_html=True)
        st.divider()
        st.markdown(
            f'<div class="sidebar-status"><span style="color:{dot};font-weight:900">●</span> {safe_text(mode)}<br><span style="color:#9fb1c4">Engine · {safe_text(engine_name)}</span></div>',
            unsafe_allow_html=True,
        )
        st.caption("Use the navigation above to switch workflows.")
        st.divider()


def render_footer() -> None:
    st.markdown(
        '<div class="footer-text"><strong>BSDI Platform</strong> · Source calculations run against the verified portfolio dataset · PKR values shown in millions</div>',
        unsafe_allow_html=True,
    )

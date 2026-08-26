"""Shared enterprise visual system for every Streamlit page."""

APP_CSS = """
<style>
:root {
  --canvas: #080909;
  --sidebar: #111312;
  --panel: #151716;
  --panel-raised: #1a1d1b;
  --line: #292d2a;
  --line-strong: #3a403b;
  --text: #f4f5f2;
  --muted: #9da39e;
  --faint: #6f756f;
  --accent: #f6c945;
  --accent-hover: #ffd968;
  --accent-ink: #171509;
  color-scheme: dark;
}

html, body, .stApp, [data-testid="stAppViewContainer"] {
  background: var(--canvas) !important;
  color: var(--text) !important;
  color-scheme: dark !important;
}
html { scroll-behavior: smooth; }
.stApp {
  background-image: linear-gradient(rgba(255,255,255,.018) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(255,255,255,.018) 1px, transparent 1px);
  background-size: 40px 40px;
}
[data-testid="stHeader"] {
  background: rgba(8, 9, 9, .92) !important;
  border-bottom: 1px solid var(--line) !important;
  backdrop-filter: blur(16px);
}
[data-testid="stMainBlockContainer"] { max-width: 1480px; padding: 1.65rem 2rem 7rem; }
[data-testid="stMain"] :is(h1, h2, h3, h4, h5, h6, p, label, li),
[data-testid="stSidebar"] :is(h1, h2, h3, h4, h5, h6, p, label, li) {
  color: var(--text);
  letter-spacing: 0;
}
[data-testid="stMain"] h1 { font-size: 1.85rem; line-height: 1.15; }
[data-testid="stMain"] h2 { font-size: 1.25rem; }
[data-testid="stMain"] h3 { font-size: 1rem; }
[data-testid="stCaptionContainer"] p { color: var(--muted) !important; }

[data-testid="stSidebar"] {
  background: var(--sidebar) !important;
  border-right: 1px solid var(--line);
  box-shadow: 16px 0 48px rgba(0,0,0,.22);
}
[data-testid="stSidebarContent"] { padding: 1rem .8rem 2rem; }
[data-testid="stSidebarNav"] { padding-top: .25rem; }
[data-testid="stSidebarNav"] li a {
  min-height: 42px;
  margin: 3px 0;
  border-radius: 6px;
  color: var(--muted);
  transition: background .16s ease, color .16s ease;
}
[data-testid="stSidebarNav"] li a:hover { background: #1b1e1c; color: var(--text); }
[data-testid="stSidebarNav"] li a[aria-current="page"] {
  color: var(--accent);
  background: rgba(246, 201, 69, .09);
  box-shadow: inset 2px 0 var(--accent);
}
.brand {
  display: flex;
  align-items: center;
  gap: .7rem;
  margin: 0 0 .9rem;
  padding: .7rem .75rem;
  border-bottom: 1px solid var(--line);
  color: var(--text) !important;
  font-size: .98rem;
  font-weight: 750;
}
.brand::before {
  content: "B";
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 6px;
  color: var(--accent-ink);
  background: var(--accent);
  font-size: .8rem;
  font-weight: 900;
}
.nav-label, .section-kicker {
  color: var(--faint) !important;
  font-size: .68rem;
  font-weight: 750;
  text-transform: uppercase;
}
.nav-label { margin: 1rem .75rem .45rem; }
.section-kicker { margin: 1.4rem 0 .65rem; }

.hero {
  position: relative;
  overflow: hidden;
  min-height: 130px;
  margin: 0 0 1rem;
  padding: 1.55rem 1.7rem;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: linear-gradient(105deg, #191c1a 0%, #101211 64%, #17160e 100%);
  box-shadow: 0 16px 38px rgba(0,0,0,.22);
}
.hero::before {
  content: "BSDI  /  OPERATIONS";
  display: block;
  margin-bottom: .8rem;
  color: var(--accent);
  font-size: .65rem;
  font-weight: 800;
}
.hero::after {
  content: "";
  position: absolute;
  right: 0;
  top: 0;
  width: 32%;
  height: 100%;
  background: linear-gradient(115deg, transparent, rgba(246,201,69,.08));
  border-left: 1px solid rgba(246,201,69,.12);
  transform: skewX(-12deg) translateX(20%);
  pointer-events: none;
}
.hero h1 { margin: 0 !important; position: relative; z-index: 1; }
.hero p {
  max-width: 760px;
  margin: .45rem 0 0;
  color: var(--muted) !important;
  font-size: .9rem;
  line-height: 1.55;
  position: relative;
  z-index: 1;
}

[data-testid="stMetric"] {
  min-height: 116px;
  padding: 1rem 1.05rem;
  border: 1px solid var(--line);
  border-radius: 7px;
  background: var(--panel);
  box-shadow: 0 10px 24px rgba(0,0,0,.16);
  transition: border-color .16s ease, transform .16s ease;
}
[data-testid="stMetric"]:hover { border-color: var(--line-strong); transform: translateY(-2px); }
[data-testid="stMetricLabel"] p { color: var(--muted) !important; font-size: .74rem; }
[data-testid="stMetricValue"] { color: var(--text) !important; font-size: 1.55rem; }
[data-testid="stMetricDelta"] { font-size: .7rem; }
div[data-testid="stPlotlyChart"], div[data-testid="stDataFrame"], div[data-testid="stJson"] {
  overflow: hidden;
  padding: .65rem;
  border: 1px solid var(--line);
  border-radius: 7px;
  background: var(--panel);
  box-shadow: 0 10px 24px rgba(0,0,0,.15);
}

.stButton button, .stDownloadButton button, [data-testid="stPageLink-NavLink"] {
  min-height: 40px;
  border: 1px solid var(--line-strong) !important;
  border-radius: 6px !important;
  color: var(--text) !important;
  background: var(--panel-raised) !important;
  transition: background .16s ease, border-color .16s ease, transform .16s ease;
}
.stButton button:hover, .stDownloadButton button:hover, [data-testid="stPageLink-NavLink"]:hover {
  border-color: var(--accent) !important;
  background: #22241f !important;
  transform: translateY(-1px);
}
.stButton button[kind="primary"] {
  border-color: var(--accent) !important;
  color: var(--accent-ink) !important;
  background: var(--accent) !important;
  font-weight: 750;
}
.stButton button[kind="primary"] p { color: var(--accent-ink) !important; }
.stButton button[kind="primary"]:hover { background: var(--accent-hover) !important; }
.stButton button:disabled { opacity: .42; transform: none; }
[data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea,
[data-testid="stNumberInput"] input, [data-baseweb="select"] > div,
[data-testid="stChatInput"] {
  border-color: var(--line-strong) !important;
  border-radius: 6px !important;
  color: var(--text) !important;
  background: var(--panel-raised) !important;
}
[data-testid="stChatInput"] textarea { color: var(--text) !important; -webkit-text-fill-color: var(--text) !important; }
[data-testid="stChatInput"] textarea::placeholder { color: var(--faint) !important; -webkit-text-fill-color: var(--faint) !important; }
[data-testid="stTabs"] [data-baseweb="tab-list"] { gap: 1.2rem; border-bottom: 1px solid var(--line); }
[data-testid="stTabs"] button[role="tab"] { color: var(--muted); padding: .7rem .1rem; }
[data-testid="stTabs"] button[aria-selected="true"] { color: var(--accent); }
[data-testid="stTabs"] [data-baseweb="tab-highlight"] { background: var(--accent); }
[data-testid="stExpander"] {
  border: 1px solid var(--line) !important;
  border-radius: 7px !important;
  background: var(--panel) !important;
}
[data-testid="stAlert"] { border-radius: 6px; }
[data-testid="stChatMessage"] {
  border: 1px solid var(--line);
  border-radius: 7px;
  background: var(--panel);
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) { border-left: 2px solid var(--accent); }
.st-key-query_conversation [data-testid="stVerticalBlockBorderWrapper"],
.st-key-query_analysis [data-testid="stVerticalBlockBorderWrapper"] {
  min-height: 540px;
  border-color: var(--line) !important;
  background: var(--panel) !important;
}
.query-panel-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 0 0 .75rem;
  padding-bottom: .65rem;
  border-bottom: 1px solid var(--line);
  color: var(--text);
  font-size: .78rem;
  font-weight: 750;
  text-transform: uppercase;
}
.query-panel-heading span { color: var(--accent); font-size: .65rem; }
.empty-analysis {
  display: grid;
  place-items: center;
  min-height: 320px;
  padding: 2rem;
  text-align: center;
  color: var(--muted);
  border: 1px dashed var(--line-strong);
  border-radius: 7px;
  background: #111311;
}

/* Force controls to paint correctly before hover in both themes. */
[data-testid="stDownloadButton"] button,
[data-testid="stDownloadButton"] button:focus,
[data-testid="stDownloadButton"] button:active {
  color: var(--text) !important;
  -webkit-text-fill-color: var(--text) !important;
  background-color: var(--panel-raised) !important;
  opacity: 1 !important;
  visibility: visible !important;
}
[data-testid="stDownloadButton"] button :is(p, span, svg) {
  color: var(--text) !important;
  fill: currentColor !important;
  opacity: 1 !important;
}
[data-testid="stDownloadButton"] button:hover { color: var(--accent) !important; }
[data-testid="stDownloadButton"] button:hover :is(p, span, svg) { color: var(--accent) !important; }
[data-baseweb="popover"], [data-baseweb="menu"], [role="listbox"] {
  color: var(--text) !important;
  background: var(--panel-raised) !important;
}
.modebar-container, .modebar, .modebar-group { background: transparent !important; }
.modebar-btn path { fill: var(--muted) !important; }
.modebar-btn:hover path, .modebar-btn.active path { fill: var(--accent) !important; }
.st-key-starter_actions {
  margin-bottom: 1rem;
  padding: 1rem;
  border: 1px solid var(--line);
  border-radius: 7px;
  background: var(--panel);
}
.starter-title { color: var(--text); font-size: .95rem; font-weight: 750; }
.starter-copy { margin: .2rem 0 .8rem; color: var(--muted); font-size: .78rem; }
[data-testid="stBottom"], [data-testid="stBottomBlockContainer"] {
  background: linear-gradient(180deg, transparent, var(--canvas) 34%) !important;
}

@media (max-width: 900px) {
  [data-testid="stMainBlockContainer"] { padding: 1rem .85rem 6rem; }
  .hero { min-height: 120px; padding: 1.25rem; }
  .hero::after { width: 20%; }
  [data-testid="stHorizontalBlock"] { flex-wrap: wrap; }
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] { min-width: 220px; }
}
@media (max-width: 560px) {
  [data-testid="stMain"] h1 { font-size: 1.45rem; }
  .hero { min-height: auto; }
  .hero::after { display: none; }
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] { min-width: 100%; }
}
</style>
"""

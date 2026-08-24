APP_CSS = """
<style>
:root { --brand:#14b8a6; --brand2:#7c3aed; --surface:#ffffff; --muted:#64748b; --ink:#132238; }
.stApp { background:radial-gradient(circle at 92% 4%,rgba(139,92,246,.13),transparent 26%),radial-gradient(circle at 8% 92%,rgba(20,184,166,.12),transparent 28%),linear-gradient(145deg,#f7fbff 0%,#f4f2ff 48%,#effcf9 100%); color:var(--ink); }
[data-testid="stHeader"] { background:rgba(247,251,255,.72); backdrop-filter:blur(14px); }
[data-testid="stMainBlockContainer"] { max-height:100vh; overflow-y:auto; padding-bottom:7rem; scroll-behavior:smooth; }
[data-testid="stSidebar"] { background:linear-gradient(170deg,#0b1224 0%,#111c38 52%,#102f38 100%); color:white; border-right:1px solid rgba(94,234,212,.22); box-shadow:12px 0 35px rgba(15,23,42,.12); }
[data-testid="stSidebar"] * { color:#e2e8f0; }
[data-testid="stSidebar"] :is(.stButton,.stDownloadButton) button { width:100%; min-height:42px; border-radius:12px; border:1px solid #334155; background:rgba(30,41,59,.82); transition:all .18s ease; }
[data-testid="stSidebar"] :is(.stButton,.stDownloadButton) button:hover { border-color:#2dd4bf; color:#5eead4; transform:translateY(-2px); box-shadow:0 8px 20px rgba(2,6,23,.25); }
[data-testid="stSidebar"] [role="radiogroup"] { gap:7px; }
[data-testid="stSidebar"] [role="radiogroup"] label { padding:9px 10px; border:1px solid rgba(148,163,184,.16); border-radius:11px; background:rgba(30,41,59,.5); transition:all .18s ease; }
[data-testid="stSidebar"] [role="radiogroup"] label:hover { border-color:rgba(94,234,212,.55); background:rgba(15,118,110,.2); transform:translateX(2px); }
.st-key-project_tools {
  margin-top:.35rem; padding:16px; border:1px solid rgba(94,234,212,.2);
  border-radius:18px; background:linear-gradient(145deg,rgba(30,41,59,.96),rgba(15,118,110,.18));
  box-shadow:0 14px 34px rgba(2,6,23,.28),inset 0 1px 0 rgba(255,255,255,.04);
}
.tools-heading { display:flex; align-items:center; gap:11px; margin-bottom:13px; }
.tools-heading .tools-icon { display:grid; place-items:center; width:34px; height:34px; border-radius:10px; color:#042f2e !important; background:linear-gradient(135deg,#5eead4,#2dd4bf); box-shadow:0 5px 15px rgba(45,212,191,.3); }
.tools-heading strong { display:block; color:#f8fafc !important; font-size:.92rem; letter-spacing:.01em; }
.tools-heading small { display:block; margin-top:1px; color:#94a3b8 !important; font-size:.7rem; }
.st-key-project_tools [data-testid="stButton"] button,
.st-key-project_tools [data-testid="stDownloadButton"] button {
  min-height:44px; margin-top:2px; border-radius:12px; font-weight:650;
  transition:transform .18s ease,box-shadow .18s ease,border-color .18s ease,background .18s ease;
}
.st-key-project_generate button { color:#042f2e !important; border:0 !important; background:linear-gradient(100deg,#5eead4,#22c55e) !important; box-shadow:0 8px 20px rgba(45,212,191,.22); }
.st-key-project_generate button:hover { color:#022c22 !important; transform:translateY(-2px); box-shadow:0 11px 24px rgba(45,212,191,.32); filter:brightness(1.06); }
.st-key-project_details button { color:#bfdbfe !important; border-color:#3b82f6 !important; background:rgba(30,64,175,.24) !important; }
.st-key-project_details button:hover { color:#eff6ff !important; background:rgba(37,99,235,.38) !important; box-shadow:0 8px 20px rgba(59,130,246,.18); }
.st-key-project_charts button { color:#ddd6fe !important; border-color:#8b5cf6 !important; background:rgba(109,40,217,.22) !important; }
.st-key-project_charts button:hover { color:#f5f3ff !important; background:rgba(124,58,237,.36) !important; box-shadow:0 8px 20px rgba(139,92,246,.18); }
.st-key-project_clear button { color:#fda4af !important; border-color:rgba(251,113,133,.42) !important; background:rgba(159,18,57,.14) !important; }
.st-key-project_clear button:hover { color:#fff1f2 !important; border-color:#fb7185 !important; background:rgba(190,18,60,.3) !important; }
.st-key-project_tools button:disabled { color:#64748b !important; border-color:#334155 !important; background:#172033 !important; box-shadow:none !important; opacity:.62; transform:none; }
.tools-status { display:flex; gap:6px; margin-top:8px; }
.tools-status span { color:#99f6e4 !important; background:rgba(13,148,136,.16); border:1px solid rgba(45,212,191,.17); border-radius:999px; padding:3px 8px; font-size:.66rem; font-weight:650; }
.brand { margin:0 0 18px; padding:14px 15px; font-size:1.22rem; font-weight:800; color:#f8fafc; letter-spacing:-.02em; border:1px solid rgba(94,234,212,.2); border-radius:15px; background:linear-gradient(120deg,rgba(20,184,166,.2),rgba(124,58,237,.18)); box-shadow:0 12px 25px rgba(2,6,23,.2); }
.brand-dot { color:#2dd4bf; }
.hero { position:relative; overflow:hidden; background:linear-gradient(125deg,#111c38 0%,#183c55 55%,#0f766e 100%); border:1px solid rgba(255,255,255,.3); border-radius:24px; padding:27px 30px; box-shadow:0 18px 45px rgba(30,41,59,.18); margin-bottom:22px; }
.hero:after { content:""; position:absolute; width:190px; height:190px; right:-45px; top:-85px; border-radius:50%; background:rgba(94,234,212,.15); box-shadow:-75px 115px 0 rgba(167,139,250,.1); }
.hero h1 { position:relative; z-index:1; margin:0; font-size:1.8rem; color:#fff; letter-spacing:-.025em; }
.hero p { position:relative; z-index:1; max-width:760px; margin:8px 0 0; color:#ccfbf1; line-height:1.55; }
[data-testid="stChatMessage"] { background:rgba(255,255,255,.88); backdrop-filter:blur(10px); border:1px solid rgba(203,213,225,.8); border-radius:19px; padding:10px 14px; box-shadow:0 8px 25px rgba(15,23,42,.06); animation:fadein .25s ease; }
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) { border-left:4px solid #8b5cf6; }
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) { border-left:4px solid #14b8a6; }
[data-testid="stChatInput"] { border-radius:18px; border:1px solid rgba(20,184,166,.25); box-shadow:0 -8px 30px rgba(15,23,42,.1); }
[data-testid="stMetric"] { background:linear-gradient(145deg,rgba(255,255,255,.95),rgba(240,253,250,.86)); border:1px solid rgba(20,184,166,.2); border-radius:17px; padding:16px; box-shadow:0 8px 24px rgba(15,23,42,.06); transition:transform .2s ease,box-shadow .2s ease; }
[data-testid="stMetric"]:hover { transform:translateY(-3px); box-shadow:0 13px 28px rgba(15,23,42,.1); }
[data-testid="stTabs"] [data-baseweb="tab-list"] { gap:8px; background:rgba(255,255,255,.7); padding:6px; border-radius:14px; box-shadow:0 5px 18px rgba(15,23,42,.05); }
[data-testid="stTabs"] button[role="tab"] { border-radius:10px; padding:8px 18px; }
[data-testid="stTabs"] button[aria-selected="true"] { color:#0f766e; background:#ccfbf1; }
div[data-testid="stPlotlyChart"],div[data-testid="stDataFrame"],div[data-testid="stJson"] { background:rgba(255,255,255,.9); border-radius:18px; padding:10px; border:1px solid rgba(203,213,225,.8); box-shadow:0 8px 24px rgba(15,23,42,.05); }
.stApp [data-testid="stMain"] .stButton button[kind="primary"] { border:0; border-radius:12px; background:linear-gradient(100deg,#0d9488,#7c3aed); box-shadow:0 8px 20px rgba(13,148,136,.2); transition:all .18s ease; }
.stApp [data-testid="stMain"] .stButton button[kind="primary"]:hover { transform:translateY(-2px); filter:brightness(1.08); box-shadow:0 12px 26px rgba(124,58,237,.25); }
@keyframes fadein { from {opacity:0; transform:translateY(4px)} to {opacity:1; transform:none} }
@media (max-width:700px) { .hero {padding:16px} .hero h1{font-size:1.3rem} }
</style>
"""

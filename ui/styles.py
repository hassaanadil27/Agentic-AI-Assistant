APP_CSS = """
<style>
:root { --brand:#0f766e; --brand2:#115e59; --surface:#ffffff; --muted:#64748b; }
.stApp { background: linear-gradient(135deg,#f8fafc 0%,#ecfeff 100%); }
[data-testid="stMainBlockContainer"] { max-height:100vh; overflow-y:auto; padding-bottom:7rem; scroll-behavior:smooth; }
[data-testid="stSidebar"] { background:#0f172a; color:white; border-right:1px solid #1e293b; }
[data-testid="stSidebar"] * { color:#e2e8f0; }
[data-testid="stSidebar"] .stButton button { width:100%; border-radius:10px; border:1px solid #334155; background:#1e293b; }
[data-testid="stSidebar"] .stButton button:hover { border-color:#2dd4bf; color:#5eead4; transform:translateY(-1px); }
.brand { padding:8px 0 18px; font-size:1.35rem; font-weight:800; color:#f8fafc; letter-spacing:-.02em; }
.brand-dot { color:#2dd4bf; }
.hero { background:rgba(255,255,255,.9); border:1px solid #dbeafe; border-radius:18px; padding:20px 24px; box-shadow:0 10px 30px rgba(15,23,42,.06); margin-bottom:18px; }
.hero h1 { margin:0; font-size:1.65rem; color:#0f172a; }
.hero p { margin:5px 0 0; color:#64748b; }
[data-testid="stChatMessage"] { background:white; border:1px solid #e2e8f0; border-radius:16px; padding:8px 12px; box-shadow:0 4px 14px rgba(15,23,42,.04); animation:fadein .2s ease; }
[data-testid="stChatInput"] { border-radius:16px; box-shadow:0 -6px 24px rgba(15,23,42,.08); }
[data-testid="stMetric"] { background:white; border:1px solid #e2e8f0; border-radius:14px; padding:14px; }
div[data-testid="stPlotlyChart"] { background:white; border-radius:16px; padding:8px; border:1px solid #e2e8f0; }
@keyframes fadein { from {opacity:0; transform:translateY(4px)} to {opacity:1; transform:none} }
@media (max-width:700px) { .hero {padding:16px} .hero h1{font-size:1.3rem} }
</style>
"""

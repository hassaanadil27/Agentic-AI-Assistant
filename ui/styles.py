"""Application-wide visual system."""

APP_CSS = """
<style>
:root { --bg:#17162b; --panel:#22213b; --panel2:#292745; --line:#39375a; --text:#f4f3ff; --muted:#aaa8c4; --teal:#25d9c7; --purple:#8b5cf6; --pink:#f05ca8; color-scheme:dark; }
html,body,[data-testid="stAppViewContainer"] { color-scheme:dark !important; background:#18172d !important; }
.stApp { color:var(--text); background:radial-gradient(circle at 70% -10%,rgba(139,92,246,.24),transparent 34%),radial-gradient(circle at 100% 90%,rgba(37,217,199,.09),transparent 30%),linear-gradient(150deg,#18172d,#201d39 55%,#17162b); }
[data-testid="stHeader"] { background:rgba(24,23,45,.8); backdrop-filter:blur(18px); border-bottom:1px solid rgba(139,92,246,.16); }
[data-testid="stMainBlockContainer"] { max-width:1240px; padding:2.2rem 2.5rem 8.5rem; scroll-behavior:smooth; }
[data-testid="stMain"] :is(h1,h2,h3,h4,h5,h6,p,li,label) { color:var(--text); }
[data-testid="stMain"] [data-testid="stCaptionContainer"], [data-testid="stMain"] [data-testid="stCaptionContainer"] p { color:var(--muted) !important; }
[data-testid="stSidebar"] { background:linear-gradient(180deg,#121126,#191831 55%,#15142a); border-right:1px solid rgba(139,92,246,.25); box-shadow:12px 0 36px rgba(4,3,16,.25); }
[data-testid="stSidebar"] * { color:#e7e5f6; }
[data-testid="stSidebarContent"] { padding:1.25rem 1rem; }
.brand { margin:0 0 17px; padding:15px; font-size:1.12rem; font-weight:850; letter-spacing:-.02em; border:1px solid rgba(139,92,246,.32); border-radius:13px; background:linear-gradient(110deg,rgba(37,217,199,.14),rgba(139,92,246,.25)); box-shadow:0 12px 28px rgba(5,4,20,.26),inset 0 1px rgba(255,255,255,.04); }
.brand:before { content:"◆"; margin-right:9px; color:var(--teal); font-size:.78rem; }
.brand-dot { color:var(--teal); }
[data-testid="stSidebar"] [role="radiogroup"] { gap:7px; }
[data-testid="stSidebar"] [role="radiogroup"] label { padding:9px 10px; border:1px solid transparent; border-radius:9px; background:rgba(255,255,255,.025); transition:.2s ease; }
[data-testid="stSidebar"] [role="radiogroup"] label:hover { border-color:rgba(139,92,246,.45); background:rgba(139,92,246,.1); transform:translateX(3px); }
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) { border-color:rgba(37,217,199,.38); background:linear-gradient(90deg,rgba(37,217,199,.14),rgba(139,92,246,.1)); box-shadow:inset 3px 0 var(--teal); }
[data-testid="stSidebar"] [role="radiogroup"] label:nth-child(2):has(input:checked) { border-color:rgba(251,191,36,.4); background:linear-gradient(90deg,rgba(251,191,36,.12),rgba(139,92,246,.08)); box-shadow:inset 3px 0 #fbbf24; }
[data-testid="stSidebar"] [role="radiogroup"] label:nth-child(3):has(input:checked) { border-color:rgba(244,63,94,.4); background:linear-gradient(90deg,rgba(244,63,94,.12),rgba(139,92,246,.08)); box-shadow:inset 3px 0 #f43f5e; }
[data-testid="stSidebar"] :is(.stButton,.stDownloadButton) button { width:100%; min-height:41px; color:#e9e7f6 !important; border:1px solid var(--line); border-radius:10px; background:#25243e; transition:.18s ease; }
[data-testid="stSidebar"] :is(.stButton,.stDownloadButton) button:hover { color:#fff !important; border-color:var(--teal); transform:translateY(-2px); box-shadow:0 9px 20px rgba(0,0,0,.22); }
[data-testid="stSidebar"] .stButton button { justify-content:flex-start; text-align:left; }
[data-testid="stSidebar"] .stButton button p { width:100%; overflow:hidden; white-space:nowrap; text-overflow:ellipsis; }
[data-testid="stSidebar"] hr { border-color:var(--line); }
.st-key-project_tools { margin-top:.3rem; padding:15px; border:1px solid rgba(37,217,199,.2); border-radius:14px; background:linear-gradient(145deg,rgba(41,39,69,.98),rgba(24,59,65,.55)); box-shadow:0 15px 32px rgba(4,3,16,.3); }
.tools-heading { display:flex; align-items:center; gap:10px; margin-bottom:12px; }
.tools-icon { display:grid; place-items:center; width:34px; height:34px; color:#101728 !important; background:linear-gradient(135deg,#50f0dd,#28c9b8); border-radius:9px; box-shadow:0 7px 16px rgba(37,217,199,.22); }
.tools-heading strong { display:block; color:#fff !important; font-size:.86rem; }
.tools-heading small { display:block; color:#9f9db9 !important; font-size:.66rem; }
.st-key-project_generate button { color:#10202c !important; border:0 !important; background:linear-gradient(100deg,#3ee4d2,#46d993) !important; box-shadow:0 8px 18px rgba(37,217,199,.2); }
.st-key-project_details button { border-color:#6962d8 !important; background:rgba(91,83,196,.2) !important; }
.st-key-project_charts button { border-color:#b657a0 !important; background:rgba(190,65,149,.16) !important; }
.st-key-project_clear button { color:#ff9ab5 !important; border-color:rgba(240,92,168,.42) !important; background:rgba(240,92,168,.08) !important; }
.st-key-project_tools button:disabled { color:#73718c !important; border-color:#37364f !important; background:#201f35 !important; opacity:.65; box-shadow:none !important; transform:none; }
.tools-status { display:flex; gap:6px; margin-top:8px; }
.tools-status span { padding:3px 8px; color:#99f6e4 !important; background:rgba(37,217,199,.09); border:1px solid rgba(37,217,199,.18); border-radius:999px; font-size:.64rem; font-weight:700; }
.hero { position:relative; overflow:hidden; padding:25px 28px; margin-bottom:20px; border:1px solid rgba(139,92,246,.28); border-radius:16px; background:linear-gradient(120deg,#24233f,#25234a 52%,#173e47); box-shadow:0 18px 40px rgba(4,3,16,.25); }
.hero:before { content:"WORKSPACE"; display:inline-block; margin-bottom:10px; padding:4px 8px; color:#b8fff6; background:rgba(37,217,199,.12); border:1px solid rgba(37,217,199,.22); border-radius:999px; font-size:.62rem; font-weight:800; letter-spacing:.13em; }
.hero:after { content:""; position:absolute; width:180px; height:180px; right:-45px; top:-90px; border-radius:50%; background:rgba(139,92,246,.2); box-shadow:-70px 120px 0 rgba(37,217,199,.1); }
.hero h1 { position:relative; z-index:1; margin:0; color:#fff !important; font-size:1.65rem; letter-spacing:-.025em; }
.hero p { position:relative; z-index:1; max-width:760px; margin:7px 0 0; color:#c8c6df !important; line-height:1.55; }
[data-testid="stChatMessage"] { color:var(--text) !important; padding:12px 15px; background:linear-gradient(145deg,rgba(42,40,70,.96),rgba(33,32,58,.96)); border:1px solid var(--line); border-radius:13px; box-shadow:0 9px 24px rgba(4,3,16,.16); animation:rise .25s ease; transition:.2s ease; }
[data-testid="stChatMessage"]:hover { border-color:rgba(139,92,246,.5); transform:translateY(-1px); }
[data-testid="stChatMessage"] :is(p,li,span,strong,em,code) { color:var(--text) !important; opacity:1 !important; }
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) { border-left:3px solid var(--purple); }
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) { border-left:3px solid var(--teal); }
[data-testid="stChatInput"] { color:var(--text) !important; background:#24233b !important; border:1px solid #474568; border-radius:13px; box-shadow:0 -9px 28px rgba(4,3,16,.25); }
[data-testid="stChatInput"] textarea { color:#f5f3ff !important; -webkit-text-fill-color:#f5f3ff !important; background:#24233b !important; caret-color:var(--teal); }
[data-testid="stChatInput"] textarea::placeholder { color:#918fab !important; -webkit-text-fill-color:#918fab !important; opacity:1; }
[data-testid="stBottom"], [data-testid="stBottomBlockContainer"] { background:linear-gradient(180deg,rgba(24,23,45,0),#18172d 28%,#18172d 100%) !important; }
[data-testid="stBottom"] > div { background:transparent !important; }
[data-testid="stBottomBlockContainer"] { padding-top:1.2rem !important; padding-bottom:1.25rem !important; }
[data-testid="stTextArea"] textarea,[data-testid="stTextInput"] input,[data-testid="stNumberInput"] input,[data-baseweb="select"]>div { color:#f5f3ff !important; -webkit-text-fill-color:#f5f3ff !important; background:#24233b !important; border-color:#464463 !important; border-radius:10px !important; }
[data-testid="stTextArea"] textarea::placeholder,[data-testid="stTextInput"] input::placeholder { color:#918fab !important; -webkit-text-fill-color:#918fab !important; opacity:1; }
[data-testid="stTextArea"] textarea:focus,[data-testid="stTextInput"] input:focus,[data-testid="stNumberInput"] input:focus { border-color:var(--teal) !important; box-shadow:0 0 0 2px rgba(37,217,199,.12) !important; }
.stApp [data-testid="stMain"] .stButton button { min-height:42px; color:#eeecfa; border:1px solid #474568; border-radius:10px; background:#292743; transition:.18s ease; }
.stApp [data-testid="stMain"] .stButton button:hover { border-color:var(--purple); transform:translateY(-2px); box-shadow:0 9px 20px rgba(4,3,16,.22); }
.stApp [data-testid="stMain"] .stButton button[kind="primary"] { color:#fff !important; border:0; background:linear-gradient(100deg,#19b8aa,#7c4ee8); box-shadow:0 8px 20px rgba(71,54,180,.24); }
.stApp [data-testid="stMain"] .stButton button[kind="primary"] :is(p,span) { color:#fff !important; }
.stApp [data-testid="stMain"] .stButton button[kind="primary"]:hover { filter:brightness(1.1); box-shadow:0 12px 26px rgba(83,61,206,.32); }
[data-testid="stMetric"] { padding:16px; background:linear-gradient(145deg,#292743,#22213a); border:1px solid #3c3a5a; border-radius:12px; box-shadow:0 8px 22px rgba(4,3,16,.16); transition:.2s ease; }
[data-testid="stMetric"]:hover { border-color:var(--teal); transform:translateY(-3px); }
[data-testid="stMetricValue"] { color:#fff; }
[data-testid="stTabs"] [data-baseweb="tab-list"] { gap:7px; padding:5px; background:#211f37; border:1px solid #363451; border-radius:11px; }
[data-testid="stTabs"] button[role="tab"] { padding:8px 16px; border-radius:8px; }
[data-testid="stTabs"] button[aria-selected="true"] { color:#bffff7; background:rgba(37,217,199,.12); }
div[data-testid="stPlotlyChart"],div[data-testid="stDataFrame"],div[data-testid="stJson"] { padding:10px; background:#22213a; border:1px solid #393756; border-radius:13px; box-shadow:0 10px 24px rgba(4,3,16,.16); }
[data-testid="stExpander"] { background:#22213a; border-color:#3b3958 !important; border-radius:11px !important; }
.starter-title { margin:4px 0 2px; color:#fff; font-size:1rem; font-weight:750; }
.starter-copy { margin:0 0 12px; color:var(--muted); font-size:.8rem; }
.st-key-starter_actions { padding:15px; margin-bottom:15px; background:rgba(34,33,58,.78); border:1px solid #383655; border-radius:13px; }
.st-key-starter_actions [data-testid="stHorizontalBlock"] { gap:9px; }
.st-key-starter_actions button { height:100%; text-align:left; background:linear-gradient(145deg,#2b2949,#25233f) !important; }
.st-key-starter_actions button:hover { border-color:var(--teal) !important; background:#302d52 !important; }
@keyframes rise { from { opacity:0; transform:translateY(5px) } to { opacity:1; transform:none } }
@media(max-width:800px) { [data-testid="stMainBlockContainer"]{padding:1.25rem 1rem 6rem}.hero{padding:20px}.hero h1{font-size:1.35rem}.st-key-starter_actions [data-testid="stHorizontalBlock"]{flex-direction:column} }
</style>
"""

"""Shared visual system for the Streamlit application."""

APP_CSS = r"""
<style>
:root {
  --ink:#10243e; --muted:#607089; --paper:#fff; --canvas:#f4f7fb;
  --line:#dfe7f1; --navy:#0b1f38; --teal:#087f78; --teal-dark:#06645f;
  --teal-soft:#e8f7f5; --blue-soft:#edf5ff; --amber:#b86a08;
  --amber-soft:#fff6df; --red:#bd3039; --red-soft:#fff0f1;
  --green:#137a52; --green-soft:#eaf8f1; --shadow:0 12px 34px rgba(15,35,61,.07);
}
html,body,[class*="css"],.stApp{font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:var(--ink)}
.stApp,[data-testid="stAppViewContainer"]{background:var(--canvas)}
[data-testid="stHeader"]{background:rgba(244,247,251,.88);border-bottom:1px solid rgba(223,231,241,.9);backdrop-filter:blur(12px)}
[data-testid="stMainBlockContainer"]{max-width:1440px;padding:1.6rem 2.4rem 5rem}
[data-testid="stMain"]{color:var(--ink)}
[data-testid="stMain"] [data-testid="stMarkdownContainer"] p,[data-testid="stMain"] [data-testid="stMarkdownContainer"] li,[data-testid="stMain"] label{color:var(--ink)}

/* Sidebar */
[data-testid="stSidebar"]{background:linear-gradient(180deg,#0b1f38 0%,#102c49 100%);border-right:0}
[data-testid="stSidebarNav"]{display:none!important}
[data-testid="stSidebar"] [data-testid="stSidebarContent"]{padding-top:.75rem}
[data-testid="stSidebar"] *{color:#dbe7f2}
[data-testid="stSidebar"] [data-testid="stSidebarNavLink"]{border-radius:10px;margin:.2rem .55rem;padding:.65rem .8rem;font-weight:600;transition:background .16s ease,transform .16s ease}
[data-testid="stSidebar"] [data-testid="stSidebarNavLink"]:hover{background:rgba(255,255,255,.08);transform:translateX(2px)}
[data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-current="page"]{background:#0d8f87;color:#fff}
[data-testid="stSidebar"] hr{border-color:rgba(255,255,255,.12)}
.sidebar-brand{display:block;padding:.8rem 1rem 1rem;margin:0 .25rem 1rem;border:1px solid rgba(255,255,255,.10);border-radius:14px;background:rgba(255,255,255,.055);text-align:center}
.sidebar-brand__eyebrow{color:#73e1d4;font-size:.68rem;font-weight:800;letter-spacing:.13em}
.sidebar-brand__title{color:#fff;font-size:1.02rem;font-weight:800;margin-top:.35rem}
.sidebar-brand__copy{color:#aabdd0;font-size:.76rem;line-height:1.5;margin-top:.35rem}
.sidebar-status{margin:.5rem .25rem;padding:.75rem 1rem;border-radius:11px;background:rgba(4,19,35,.34);font-size:.76rem;line-height:1.6}
[data-testid="stSidebar"] [data-testid="stPageLink"] a{color:#dbe7f2!important;background:transparent!important;border:1px solid transparent!important;justify-content:flex-start;padding:.62rem .75rem!important;margin:.08rem 0}
[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover{color:#fff!important;background:rgba(255,255,255,.08)!important;border-color:rgba(255,255,255,.06)!important}
[data-testid="stSidebar"] [data-testid="stPageLink"] a[aria-current="page"]{color:#fff!important;background:#0d8f87!important}
.sidebar-fallback-link{display:block;color:#dbe7f2!important;text-decoration:none;padding:.72rem .8rem;margin:.08rem 0;border-radius:9px;font-size:.88rem;font-weight:700}.sidebar-fallback-link:hover{color:#fff!important;background:rgba(255,255,255,.08)}
[data-testid="stLogo"]{height:118px!important;margin:.1rem auto .35rem!important;display:flex!important;justify-content:center!important;overflow:visible!important}
[data-testid="stLogo"] img{width:112px!important;height:108px!important;object-fit:contain!important;filter:drop-shadow(0 7px 14px rgba(0,0,0,.22))}

/* Header */
.app-header{position:relative;overflow:hidden;display:flex;justify-content:space-between;align-items:flex-start;gap:1.5rem;padding:1.75rem 1.9rem;margin-bottom:1.35rem;color:#fff;background:linear-gradient(120deg,#0b1f38 0%,#123b55 65%,#087f78 130%);border-radius:18px;box-shadow:var(--shadow)}
.app-header:after{content:"";position:absolute;width:220px;height:220px;right:-85px;top:-120px;border-radius:50%;border:35px solid rgba(255,255,255,.055)}
.app-header__content{position:relative;z-index:1;max-width:900px}
.app-header__identity{position:relative;z-index:1;display:flex;align-items:center;gap:1rem}
.app-header__eyebrow{color:#72ded2;font-size:.7rem;font-weight:800;letter-spacing:.14em;text-transform:uppercase}
.app-header h1{color:#fff!important;font-size:clamp(1.55rem,3vw,2.15rem)!important;line-height:1.14;letter-spacing:-.035em;margin:.4rem 0 .45rem!important}
.app-header p{color:#c9d8e7!important;font-size:.94rem!important;line-height:1.55;margin:0!important;max-width:780px}
.app-header__badge{position:relative;z-index:1;white-space:nowrap;margin-top:.15rem}

/* Components */
.section-heading{margin:1.7rem 0 .8rem}.section-heading__row{display:flex;align-items:center;gap:.65rem}.section-heading__accent{width:4px;height:22px;border-radius:4px;background:var(--teal)}
.section-heading h2{font-size:1.12rem!important;color:var(--ink)!important;letter-spacing:-.015em;margin:0!important}.section-heading p{color:var(--muted);font-size:.82rem;margin:.25rem 0 0 .65rem}
.stat-card{height:100%;min-height:124px;padding:1.05rem 1.15rem;background:var(--paper);border:1px solid var(--line);border-radius:14px;box-shadow:0 2px 8px rgba(15,35,61,.035)}
.stat-card__top{display:flex;align-items:center;justify-content:space-between;gap:.5rem}.stat-label{color:var(--muted);font-size:.69rem;font-weight:800;letter-spacing:.075em;text-transform:uppercase}
.stat-value{color:var(--ink);font-size:clamp(1.35rem,2.2vw,1.85rem);font-weight:800;letter-spacing:-.035em;margin:.55rem 0 .25rem;line-height:1.05}.stat-desc{color:var(--muted);font-size:.77rem;line-height:1.4}
.badge{display:inline-flex;align-items:center;gap:.3rem;border-radius:999px;padding:.28rem .58rem;font-size:.67rem;font-weight:800;line-height:1;border:1px solid transparent}
.badge-green{color:var(--green);background:var(--green-soft);border-color:#c6ead8}.badge-blue{color:#245d97;background:var(--blue-soft);border-color:#d1e5fb}.badge-amber{color:var(--amber);background:var(--amber-soft);border-color:#f3ddb1}.badge-red{color:var(--red);background:var(--red-soft);border-color:#f2c9cd}.badge-neutral{color:var(--muted);background:#f2f5f8;border-color:var(--line)}
.workflow-card{min-height:158px;padding:1.25rem;border:1px solid var(--line);border-radius:15px;background:#fff;box-shadow:0 3px 12px rgba(15,35,61,.035)}
.workflow-card__icon{width:39px;height:39px;display:grid;place-items:center;border-radius:10px;background:var(--teal-soft);color:var(--teal);font-size:1.15rem}.workflow-card h3{color:var(--ink)!important;font-size:1rem!important;margin:.8rem 0 .35rem!important}.workflow-card p{color:var(--muted);font-size:.8rem;line-height:1.55;margin:0}
.track-card{height:100%;min-height:165px;padding:1rem 1.05rem;background:#fff;border:1px solid var(--line);border-top:4px solid #2563eb;border-radius:13px;box-shadow:0 3px 12px rgba(15,35,61,.04)}
.track-card--green{border-top-color:var(--green)}.track-card--amber{border-top-color:#d97706}.track-card--teal{border-top-color:var(--teal)}
.track-card__top{display:flex;justify-content:space-between;gap:.5rem;align-items:center}.track-card__top strong{color:var(--ink);font-size:.92rem}.track-card__top span{font-size:.65rem;font-weight:800;color:var(--green);background:var(--green-soft);padding:.25rem .5rem;border-radius:999px}
.track-card p{color:var(--muted);font-size:.78rem;line-height:1.5;margin:.55rem 0}.track-card__activity{color:#31506e;background:#f3f7fb;border-radius:8px;padding:.55rem .65rem;font-size:.73rem;line-height:1.45}.track-card__activity b{color:var(--ink)}
.callout{padding:.9rem 1rem;border-radius:12px;border:1px solid #cbe8e4;background:var(--teal-soft);color:#165a57;font-size:.82rem;line-height:1.55}
.empty-state{padding:2.5rem 1.25rem;text-align:center;background:#fff;border:1px dashed #cbd7e4;border-radius:14px;color:var(--muted)}.empty-state__icon{font-size:1.55rem;margin-bottom:.55rem}.empty-state strong{display:block;color:var(--ink);margin-bottom:.25rem}
.trace-step{display:flex;gap:.7rem;padding:.65rem .2rem;border-bottom:1px solid var(--line);font-size:.8rem}.trace-step__tag{min-width:72px;color:var(--teal);font-weight:800;font-size:.69rem;letter-spacing:.05em}.trace-step__body{color:var(--muted);word-break:break-word}
.footer-text{color:#8a98aa;text-align:center;font-size:.72rem;border-top:1px solid var(--line);padding-top:1.2rem;margin-top:2.8rem}

/* Widgets */
[data-testid="stVerticalBlockBorderWrapper"]{background:#fff;border-color:var(--line)!important;border-radius:14px!important;box-shadow:0 2px 9px rgba(15,35,61,.03)}
.stButton>button,.stDownloadButton>button,[data-testid="stPageLink"] a{border-radius:9px!important;min-height:2.55rem;font-weight:700!important;transition:transform .15s ease,box-shadow .15s ease,border-color .15s ease}
.stButton>button:hover,.stDownloadButton>button:hover,[data-testid="stPageLink"] a:hover{transform:translateY(-1px);border-color:var(--teal)!important}.stButton>button[kind="primary"]{background:var(--teal)!important;border-color:var(--teal-dark)!important;color:#fff!important}.stButton>button[kind="primary"]:hover{background:var(--teal-dark)!important;box-shadow:0 5px 14px rgba(8,127,120,.18)}
.stDownloadButton>button{background:#123b55!important;border-color:#123b55!important;color:#fff!important}.stDownloadButton>button:hover{background:#087f78!important;color:#fff!important;box-shadow:0 5px 14px rgba(8,127,120,.18)}
[data-baseweb="input"]>div,[data-baseweb="select"]>div,[data-baseweb="textarea"]{border-color:#d5e0eb!important;border-radius:9px!important;background:#fff!important}
[data-testid="stChatMessage"]{color:#17324f!important;background:#fff!important;border:1px solid #d8e3ee;border-radius:14px;padding:1rem 1.1rem;margin-bottom:.75rem;box-shadow:0 3px 10px rgba(15,35,61,.045)}
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"],[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p,[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] li,[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] strong,[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] em{color:#17324f!important;opacity:1!important}
[data-testid="stChatMessage"] [data-testid="stCaptionContainer"],[data-testid="stChatMessage"] [data-testid="stCaptionContainer"] p{color:#6b7d91!important;opacity:1!important}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]),[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]){border-left:4px solid var(--teal);background:#fff!important}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]),[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]){background:#eef5fb!important;border-color:#d5e3f0}
[data-testid="stChatMessageAvatarAssistant"]{background:#087f78!important}[data-testid="stChatMessageAvatarUser"]{background:#315d88!important}
[data-testid="stBottom"]{background:linear-gradient(180deg,rgba(244,247,251,0),#f4f7fb 28%)!important}
[data-testid="stChatInput"]{background:#fff!important;border:1px solid #cfdce8!important;border-radius:13px;box-shadow:0 8px 24px rgba(15,35,61,.11)}
[data-testid="stChatInput"] textarea{color:#10243e!important;-webkit-text-fill-color:#10243e!important;caret-color:#087f78!important;background:#fff!important}
[data-testid="stChatInput"] textarea::placeholder{color:#718196!important;opacity:1!important}
[data-testid="stChatInput"] button{color:#fff!important;background:#087f78!important;border-radius:9px!important}
[data-testid="stDataFrame"]{border:1px solid var(--line);border-radius:12px;overflow:hidden}[data-testid="stExpander"]{background:#fff;border-color:var(--line)!important;border-radius:11px!important}[data-testid="stAlert"]{border-radius:11px}[data-baseweb="tab-list"]{gap:.35rem}[data-baseweb="tab"]{border-radius:8px 8px 0 0;font-weight:700}
@media(max-width:900px){[data-testid="stMainBlockContainer"]{padding:1.15rem 1rem 4rem}.app-header{padding:1.35rem;flex-direction:column}.app-header__badge{margin-top:0}.stat-card{min-height:112px}}
@media(prefers-reduced-motion:reduce){*{transition:none!important;scroll-behavior:auto!important}}
</style>
"""

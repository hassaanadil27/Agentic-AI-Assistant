"""Application-wide visual system with modern colorful design."""

APP_CSS = """
<style>
:root {
  --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  --secondary-gradient: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  --accent-gradient: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
  --success-gradient: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
  --warning-gradient: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
  
  --bg-primary: #0f0f1e;
  --bg-secondary: #1a1a2e;
  --bg-tertiary: #252540;
  --bg-elevated: #2d2d48;
  
  --text-primary: #ffffff;
  --text-secondary: #c7c7e0;
  --text-tertiary: #9999b3;
  
  --border-color: #404060;
  --border-light: #505080;
  
  color-scheme: dark;
}

html, body, [data-testid="stAppViewContainer"] {
  color-scheme: dark !important;
  background: linear-gradient(135deg, #0f0f1e 0%, #1a1a2e 50%, #16213e 100%) !important;
}

.stApp {
  color: var(--text-primary);
  background:
    radial-gradient(circle at 20% 50%, rgba(102, 126, 234, 0.15), transparent 50%),
    radial-gradient(circle at 80% 80%, rgba(240, 147, 251, 0.1), transparent 50%),
    radial-gradient(circle at 50% 0%, rgba(79, 172, 254, 0.08), transparent 50%),
    linear-gradient(135deg, #0f0f1e 0%, #1a1a2e 50%, #16213e 100%);
}

/* Header */
[data-testid="stHeader"] {
  background: rgba(26, 26, 46, 0.8) !important;
  backdrop-filter: blur(20px) !important;
  border-bottom: 2px solid rgba(102, 126, 234, 0.3) !important;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3) !important;
}

/* Main Container */
[data-testid="stMainBlockContainer"] {
  max-width: 1400px;
  padding: 2.5rem 3rem 8rem;
  scroll-behavior: smooth;
}

/* Main Text */
[data-testid="stMain"] :is(h1, h2, h3, h4, h5, h6, p, li, label) {
  color: var(--text-primary);
}

[data-testid="stMain"] [data-testid="stCaptionContainer"],
[data-testid="stMain"] [data-testid="stCaptionContainer"] p {
  color: var(--text-tertiary) !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #1a1a2e 0%, #16213e 50%, #0f1621 100%);
  border-right: 2px solid rgba(102, 126, 234, 0.2);
  box-shadow: 12px 0 36px rgba(0, 0, 0, 0.4);
}

[data-testid="stSidebar"] * {
  color: var(--text-primary);
}

[data-testid="stSidebarContent"] {
  padding: 1.5rem 1.25rem;
}

/* Brand Logo */
.brand {
  margin: 0 0 20px;
  padding: 16px 18px;
  font-size: 1.2rem;
  font-weight: 900;
  letter-spacing: -0.02em;
  border: 2px solid rgba(102, 126, 234, 0.4);
  border-radius: 14px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.2), rgba(240, 147, 251, 0.15));
  box-shadow: 0 12px 28px rgba(102, 126, 234, 0.2), inset 0 1px rgba(255, 255, 255, 0.1);
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.brand:before {
  content: "◆";
  margin-right: 10px;
  color: #667eea;
  font-size: 0.8rem;
}

.brand-dot {
  color: #f093fb;
}

/* Radio Group Styling */
[data-testid="stSidebar"] [role="radiogroup"] {
  gap: 8px;
  display: flex;
  flex-direction: column;
}

[data-testid="stSidebar"] [role="radiogroup"] label {
  padding: 12px 14px;
  border: 1.5px solid var(--border-color);
  border-radius: 10px;
  background: rgba(45, 45, 72, 0.6);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
}

[data-testid="stSidebar"] [role="radiogroup"] label:hover {
  border-color: rgba(102, 126, 234, 0.6);
  background: rgba(102, 126, 234, 0.15);
  transform: translateX(4px);
}

[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
  border-color: rgba(102, 126, 234, 0.8);
  background: linear-gradient(90deg, rgba(102, 126, 234, 0.25), rgba(118, 75, 162, 0.15));
  box-shadow: inset 4px 0 #667eea;
}

/* Sidebar Buttons */
[data-testid="stSidebar"] :is(.stButton, .stDownloadButton) button {
  width: 100%;
  min-height: 44px;
  color: var(--text-primary) !important;
  border: 1.5px solid var(--border-color);
  border-radius: 10px;
  background: linear-gradient(135deg, rgba(45, 45, 72, 0.8), rgba(37, 37, 64, 0.8));
  transition: all 0.3s ease;
}

[data-testid="stSidebar"] :is(.stButton, .stDownloadButton) button:hover {
  color: #fff !important;
  border-color: rgba(102, 126, 234, 0.6);
  transform: translateY(-2px);
  box-shadow: 0 12px 24px rgba(102, 126, 234, 0.3);
}

[data-testid="stSidebar"] .stButton button {
  justify-content: flex-start;
  text-align: left;
}

[data-testid="stSidebar"] .stButton button p {
  width: 100%;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

[data-testid="stSidebar"] hr {
  border-color: var(--border-color);
}

/* Project Tools Section */
.st-key-project_tools {
  margin-top: 0.5rem;
  padding: 18px;
  border: 1.5px solid rgba(102, 126, 234, 0.3);
  border-radius: 14px;
  background: linear-gradient(145deg, rgba(37, 37, 64, 0.95), rgba(26, 26, 46, 0.95));
  box-shadow: 0 15px 32px rgba(102, 126, 234, 0.15);
}

.tools-heading {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}

.tools-icon {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  color: #0f0f1e !important;
  background: var(--accent-gradient);
  border-radius: 10px;
  box-shadow: 0 8px 20px rgba(79, 172, 254, 0.3);
}

.tools-heading strong {
  display: block;
  color: #fff !important;
  font-size: 0.9rem;
}

.tools-heading small {
  display: block;
  color: var(--text-tertiary) !important;
  font-size: 0.7rem;
}

.st-key-project_generate button {
  color: #0f0f1e !important;
  border: 0 !important;
  background: var(--success-gradient) !important;
  box-shadow: 0 8px 20px rgba(67, 233, 123, 0.3) !important;
}

.st-key-project_details button {
  border-color: rgba(102, 126, 234, 0.5) !important;
  background: rgba(102, 126, 234, 0.15) !important;
}

.st-key-project_charts button {
  border-color: rgba(240, 147, 251, 0.5) !important;
  background: rgba(240, 147, 251, 0.15) !important;
}

.st-key-project_clear button {
  color: #ff9ab5 !important;
  border-color: rgba(240, 92, 168, 0.5) !important;
  background: rgba(240, 92, 168, 0.1) !important;
}

.st-key-project_tools button:disabled {
  color: var(--text-tertiary) !important;
  border-color: var(--border-color) !important;
  background: var(--bg-tertiary) !important;
  opacity: 0.5;
  box-shadow: none !important;
  transform: none;
}

.tools-status {
  display: flex;
  gap: 8px;
  margin-top: 10px;
  flex-wrap: wrap;
}

.tools-status span {
  padding: 4px 10px;
  color: var(--text-primary) !important;
  background: rgba(79, 172, 254, 0.15);
  border: 1px solid rgba(79, 172, 254, 0.3);
  border-radius: 999px;
  font-size: 0.65rem;
  font-weight: 700;
}

/* Hero Section */
.hero {
  position: relative;
  overflow: hidden;
  padding: 32px 36px;
  margin-bottom: 24px;
  border: 2px solid rgba(102, 126, 234, 0.3);
  border-radius: 16px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.15), rgba(240, 147, 251, 0.1));
  box-shadow: 0 20px 48px rgba(102, 126, 234, 0.2);
}

.hero:before {
  content: "WORKSPACE";
  display: inline-block;
  margin-bottom: 12px;
  padding: 6px 12px;
  color: #fff;
  background: var(--accent-gradient);
  border: none;
  border-radius: 999px;
  font-size: 0.65rem;
  font-weight: 900;
  letter-spacing: 0.15em;
}

.hero:after {
  content: "";
  position: absolute;
  width: 220px;
  height: 220px;
  right: -60px;
  top: -100px;
  border-radius: 50%;
  background: rgba(240, 147, 251, 0.2);
  box-shadow: -80px 140px 0 rgba(102, 126, 234, 0.15);
}

.hero h1 {
  position: relative;
  z-index: 1;
  margin: 0;
  color: #fff !important;
  font-size: 1.8rem;
  letter-spacing: -0.025em;
  background: linear-gradient(135deg, #667eea, #f093fb);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.hero p {
  position: relative;
  z-index: 1;
  max-width: 800px;
  margin: 10px 0 0;
  color: var(--text-secondary) !important;
  line-height: 1.6;
}

/* Chat Messages */
[data-testid="stChatMessage"] {
  color: var(--text-primary) !important;
  padding: 14px 18px;
  background: linear-gradient(135deg, rgba(45, 45, 72, 0.95), rgba(37, 37, 64, 0.95));
  border: 1.5px solid var(--border-color);
  border-radius: 14px;
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.2);
  animation: rise 0.3s ease;
  transition: all 0.2s ease;
}

[data-testid="stChatMessage"]:hover {
  border-color: rgba(102, 126, 234, 0.5);
  transform: translateY(-2px);
  box-shadow: 0 14px 36px rgba(102, 126, 234, 0.15);
}

[data-testid="stChatMessage"] :is(p, li, span, strong, em, code) {
  color: var(--text-primary) !important;
  opacity: 1 !important;
}

[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
  border-left: 4px solid #667eea;
}

[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
  border-left: 4px solid #4facfe;
}

/* Chat Input */
[data-testid="stChatInput"] {
  color: var(--text-primary) !important;
  background: var(--bg-tertiary) !important;
  border: 1.5px solid var(--border-color) !important;
  border-radius: 14px !important;
  box-shadow: 0 -8px 28px rgba(102, 126, 234, 0.15) !important;
}

[data-testid="stChatInput"] textarea {
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
  background: var(--bg-tertiary) !important;
  caret-color: #667eea;
}

[data-testid="stChatInput"] textarea::placeholder {
  color: var(--text-tertiary) !important;
  -webkit-text-fill-color: var(--text-tertiary) !important;
  opacity: 1;
}

/* Bottom */
[data-testid="stBottom"],
[data-testid="stBottomBlockContainer"] {
  background: linear-gradient(180deg, rgba(15, 15, 30, 0), #0f0f1e 30%, #0f0f1e 100%) !important;
}

[data-testid="stBottom"] > div {
  background: transparent !important;
}

[data-testid="stBottomBlockContainer"] {
  padding-top: 1.5rem !important;
  padding-bottom: 1.5rem !important;
}

/* Inputs */
[data-testid="stTextArea"] textarea,
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-baseweb="select"] > div {
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
  background: var(--bg-tertiary) !important;
  border-color: var(--border-color) !important;
  border-radius: 10px !important;
}

[data-testid="stTextArea"] textarea::placeholder,
[data-testid="stTextInput"] input::placeholder {
  color: var(--text-tertiary) !important;
  -webkit-text-fill-color: var(--text-tertiary) !important;
  opacity: 1;
}

[data-testid="stTextArea"] textarea:focus,
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus {
  border-color: #667eea !important;
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2) !important;
}

/* Main Buttons */
.stApp [data-testid="stMain"] .stButton button {
  min-height: 44px;
  color: var(--text-primary);
  border: 1.5px solid var(--border-color);
  border-radius: 10px;
  background: linear-gradient(135deg, rgba(45, 45, 72, 0.9), rgba(37, 37, 64, 0.9));
  transition: all 0.3s ease;
}

.stApp [data-testid="stMain"] .stButton button:hover {
  border-color: rgba(102, 126, 234, 0.6);
  transform: translateY(-2px);
  box-shadow: 0 10px 24px rgba(102, 126, 234, 0.2);
}

.stApp [data-testid="stMain"] .stButton button[kind="primary"] {
  color: #fff !important;
  border: 0;
  background: var(--primary-gradient) !important;
  box-shadow: 0 10px 28px rgba(102, 126, 234, 0.3) !important;
}

.stApp [data-testid="stMain"] .stButton button[kind="primary"] :is(p, span) {
  color: #fff !important;
}

.stApp [data-testid="stMain"] .stButton button[kind="primary"]:hover {
  filter: brightness(1.15);
  box-shadow: 0 14px 36px rgba(102, 126, 234, 0.4) !important;
}

/* Metrics */
[data-testid="stMetric"] {
  padding: 18px;
  background: linear-gradient(135deg, rgba(45, 45, 72, 0.9), rgba(37, 37, 64, 0.9));
  border: 1.5px solid var(--border-color);
  border-radius: 12px;
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.2);
  transition: all 0.3s ease;
}

[data-testid="stMetric"]:hover {
  border-color: rgba(102, 126, 234, 0.6);
  transform: translateY(-4px);
  box-shadow: 0 14px 36px rgba(102, 126, 234, 0.2);
}

[data-testid="stMetricValue"] {
  color: #fff;
}

/* Tabs */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
  gap: 8px;
  padding: 6px;
  background: var(--bg-tertiary);
  border: 1.5px solid var(--border-color);
  border-radius: 12px;
}

[data-testid="stTabs"] button[role="tab"] {
  padding: 10px 18px;
  border-radius: 8px;
  transition: all 0.2s ease;
}

[data-testid="stTabs"] button[aria-selected="true"] {
  color: #fff;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.3), rgba(118, 75, 162, 0.2));
}

/* Data Containers */
div[data-testid="stPlotlyChart"],
div[data-testid="stDataFrame"],
div[data-testid="stJson"] {
  padding: 12px;
  background: linear-gradient(135deg, rgba(45, 45, 72, 0.95), rgba(37, 37, 64, 0.95));
  border: 1.5px solid var(--border-color);
  border-radius: 14px;
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.2);
}

/* Expander */
[data-testid="stExpander"] {
  background: linear-gradient(135deg, rgba(45, 45, 72, 0.9), rgba(37, 37, 64, 0.9));
  border-color: var(--border-color) !important;
  border-radius: 12px !important;
  border: 1.5px solid !important;
}

/* Starter Actions */
.starter-title {
  margin: 6px 0 4px;
  color: #fff;
  font-size: 1.1rem;
  font-weight: 800;
}

.starter-copy {
  margin: 0 0 14px;
  color: var(--text-secondary);
  font-size: 0.85rem;
}

.st-key-starter_actions {
  padding: 18px;
  margin-bottom: 18px;
  background: linear-gradient(135deg, rgba(45, 45, 72, 0.8), rgba(37, 37, 64, 0.8));
  border: 1.5px solid rgba(102, 126, 234, 0.3);
  border-radius: 14px;
}

.st-key-starter_actions [data-testid="stHorizontalBlock"] {
  gap: 12px;
}

.st-key-starter_actions button {
  height: 100%;
  text-align: left;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.15), rgba(240, 147, 251, 0.1)) !important;
  border: 1.5px solid rgba(102, 126, 234, 0.3) !important;
}

.st-key-starter_actions button:hover {
  border-color: rgba(102, 126, 234, 0.6) !important;
  background: rgba(102, 126, 234, 0.25) !important;
  transform: translateY(-2px);
}

/* Animations */
@keyframes rise {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.8;
  }
}

/* Responsive */
@media (max-width: 800px) {
  [data-testid="stMainBlockContainer"] {
    padding: 1.25rem 1rem 6rem;
  }
  .hero {
    padding: 24px;
  }
  .hero h1 {
    font-size: 1.4rem;
  }
  .st-key-starter_actions [data-testid="stHorizontalBlock"] {
    flex-direction: column;
  }
}
</style>
"""

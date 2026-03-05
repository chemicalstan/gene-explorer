import os
import requests
import streamlit as st
import streamlit.components.v1 as components

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Gene Explorer", page_icon="🧬", layout="centered")

# ── Global styles ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Base ─────────────────────────────────────────────────────────────────── */
.stApp,[data-testid="stAppViewContainer"],[data-testid="stMain"]{
  background:#f5ece6!important}
#MainMenu,footer,header{visibility:hidden!important}
[data-testid="stHeader"]{display:none!important}
[data-testid="stToolbar"]{display:none!important}
[data-testid="stDecoration"]{display:none!important}
button[title="View fullscreen"]{display:none!important}
.block-container{max-width:720px;padding-top:2.5rem;padding-bottom:7rem}

/* ── Mode badge pulse ─────────────────────────────────────────────────────── */
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
.mode-dot{display:inline-block;width:8px;height:8px;border-radius:50%;
  margin-right:7px;vertical-align:middle;animation:pulse 2s ease-in-out infinite}

/* ── Example buttons ─────────────────────────────────────────────────────── */
.stButton>button{
  background:#fff!important;color:#2a2a2a!important;
  border:1.5px solid #ddd0c8!important;border-radius:12px!important;
  font-size:.84rem!important;white-space:normal!important;
  height:auto!important;min-height:52px!important;
  padding:.65rem 1rem!important;text-align:left!important;
  box-shadow:0 1px 4px rgba(0,0,0,.06)!important;
  transition:all .15s ease!important;line-height:1.4!important}
.stButton>button:hover{
  border-color:#b87050!important;
  box-shadow:0 4px 14px rgba(0,0,0,.13)!important;
  transform:translateY(-1px)!important;color:#1a1a1a!important}
.stButton>button:active{transform:translateY(0)!important}

/* ── Chat messages ───────────────────────────────────────────────────────── */
[data-testid="stChatMessage"]{
  background:#fff!important;border:1px solid #e8ddd6!important;
  border-radius:16px!important;margin-bottom:.7rem!important;
  box-shadow:0 2px 8px rgba(0,0,0,.06)!important;padding:.1rem .2rem!important}
[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] li,
[data-testid="stChatMessage"] span,
[data-testid="stChatMessage"] div,
[data-testid="stChatMessage"] strong,
[data-testid="stChatMessage"] em,
[data-testid="stChatMessage"] code{color:#1a1a1a!important}
[data-testid="stChatMessage"] code{background:#f2ebe5!important}

/* ── Bottom bar ──────────────────────────────────────────────────────────── */
[data-testid="stBottom"]>div{
  background:#f5ece6!important;
  border-top:1px solid #e0d4cd!important;
  padding:.6rem 0!important}

/* ── Chat input container ────────────────────────────────────────────────── */
[data-testid="stChatInputContainer"]{
  background:#fff!important;
  border:1.5px solid #cfc4bc!important;
  border-radius:14px!important;
  box-shadow:0 3px 12px rgba(0,0,0,.09)!important}
[data-testid="stChatInputContainer"] textarea{
  color:#1a1a1a!important;font-size:.95rem!important;background:transparent!important}
[data-testid="stChatInputContainer"] textarea::placeholder{color:#b5aca5!important}
[data-testid="stChatInputContainer"] button{
  background:#c07050!important;border-radius:10px!important}
[data-testid="stChatInputContainer"] button:hover{background:#a85c3c!important}
[data-testid="stChatInputContainer"] button svg{fill:#fff!important}

/* ── Caption / divider / label ───────────────────────────────────────────── */
.stCaption,[data-testid="stCaptionContainer"],small{color:#9a8f88!important}
label,p,span,div{color:#1a1a1a}
[data-testid="stMarkdownContainer"] p{color:#1a1a1a!important}
hr{border-color:#e0d4cd!important}
</style>
""", unsafe_allow_html=True)

# ── State ──────────────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending" not in st.session_state:
    st.session_state.pending = None


# ── Backend helpers ────────────────────────────────────────────────────────────



def get_reply(message: str) -> tuple[str, list]:
    try:
        r = requests.post(
            f"{BACKEND_URL}/chat",
            json={"message": message},
            timeout=180,
        )
        r.raise_for_status()
        d = r.json()
        return d["answer"], d.get("tool_calls_made", [])
    except requests.exceptions.ConnectionError:
        return f"Cannot reach the backend at `{BACKEND_URL}`.", []
    except requests.exceptions.Timeout:
        return "Request timed out — try again shortly.", []
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 500:
            return "Something went wrong on the server. Please try again.", []
        return "Unexpected response from the server. Please try again.", []
    except Exception:
        return "An unexpected error occurred. Please try again.", []


# ── Header ─────────────────────────────────────────────────────────────────────
mode, provider = get_health()

if mode == "llm":
    dot_color = "#4caf8a"
    badge_label = f"LLM mode &nbsp;·&nbsp; {provider.capitalize()}"
elif mode == "deterministic":
    dot_color = "#c8a040"
    badge_label = "Deterministic mode"
else:
    dot_color = "#cc5555"
    badge_label = "Backend offline"

st.markdown(
    f'<h1 style="text-align:center;font-size:2.2rem;font-weight:800;'
    f'color:#1a1a1a;letter-spacing:-.5px;margin-bottom:.25rem">🧬 Gene Explorer</h1>',
    unsafe_allow_html=True,
)
st.markdown(
    f'<p style="text-align:center;color:#888;font-size:.93rem;margin-top:0;margin-bottom:.6rem">'
    f'Ask questions about cancer gene expression data</p>',
    unsafe_allow_html=True,
)
st.markdown(
    f'<div style="text-align:center;margin-bottom:1.8rem">'
    f'<span style="display:inline-flex;align-items:center;background:#fff;'
    f'border:1px solid #ddd0c8;border-radius:999px;padding:5px 16px;'
    f'font-size:.78rem;color:#666;box-shadow:0 1px 4px rgba(0,0,0,.06)">'
    f'<span class="mode-dot" style="background:{dot_color}"></span>'
    f'{badge_label}</span></div>',
    unsafe_allow_html=True,
)

# ── Example buttons (2 × 2) ───────────────────────────────────────────────────
EXAMPLES = [
    "How can you help me?",
    "What are the main genes involved in lung cancer?",
    "What is the median expression of genes in breast cancer?",
    "What about esophageal cancer?",
]

st.markdown(
    '<p style="font-size:.72rem;font-weight:600;letter-spacing:.08em;'
    'color:#aaa;margin-bottom:.4rem">TRY AN EXAMPLE</p>',
    unsafe_allow_html=True,
)
c1, c2 = st.columns(2)
for i, q in enumerate(EXAMPLES):
    if (c1 if i % 2 == 0 else c2).button(q, key=f"ex{i}", use_container_width=True):
        st.session_state.pending = q

# ── Chat history ───────────────────────────────────────────────────────────────
if st.session_state.messages:
    st.markdown("<hr style='margin:1.2rem 0 .8rem'>", unsafe_allow_html=True)
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── Input ──────────────────────────────────────────────────────────────────────
prompt = st.chat_input("Ask me about cancer genes…")

if not prompt and st.session_state.pending:
    prompt = st.session_state.pending
    st.session_state.pending = None

# ── Process ────────────────────────────────────────────────────────────────────
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            reply, tool_calls = get_reply(prompt)
        st.markdown(reply)
        if tool_calls:
            st.caption("Tools used: " + "  ·  ".join(f"🔧 {t}" for t in tool_calls))

    st.session_state.messages.append({"role": "assistant", "content": reply})

# ── Auto-scroll to bottom whenever there are messages ─────────────────────────
if st.session_state.messages:
    components.html(
        """
        <script>
          // Give Streamlit's DOM a moment to finish painting, then snap to bottom
          setTimeout(function () {
            var main = window.parent.document.querySelector('[data-testid="stMain"]');
            if (main) { main.scrollTop = main.scrollHeight; }
          }, 120);
        </script>
        """,
        height=0,
    )

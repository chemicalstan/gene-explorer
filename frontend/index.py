"""Gene Explorer chat UI.

Presentation comes from .streamlit/config.toml and native Streamlit components.
There are no CSS overrides of Streamlit internals and no injected scripts, so an
upgrade of Streamlit cannot silently break the layout.
"""

import os
import uuid

import streamlit as st
from api_client import GeneExplorerClient

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
API_KEY = os.getenv("GENE_EXPLORER_API_KEY") or None

EXAMPLES = [
    "What genes are involved in lung cancer?",
    "What is the median expression of genes in breast cancer?",
    "What about prostate cancer?",
    "What genes are involved in esophageal cancer?",
]

st.set_page_config(page_title="Gene Explorer", page_icon="🧬", layout="centered")


@st.cache_resource
def get_client() -> GeneExplorerClient:
    return GeneExplorerClient(BACKEND_URL, api_key=API_KEY)


@st.cache_data(ttl=30)
def get_health() -> tuple[bool, str | None]:
    health = get_client().health()
    return health.online, health.model


def init_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "session_id" not in st.session_state:
        # One conversation per browser session, so follow-up questions work.
        st.session_state.session_id = str(uuid.uuid4())
    if "pending" not in st.session_state:
        st.session_state.pending = None


def render_header() -> None:
    st.title("🧬 Gene Explorer")
    st.caption("Ask questions about cancer gene expression data.")

    online, model = get_health()
    if not online:
        st.error(f"The service is unreachable at {BACKEND_URL}.", icon="🔌")
        return
    if get_client().supports_sessions:
        st.caption(f"Connected · {model} · follow-up questions enabled")
    else:
        st.caption(f"Connected · {model}")
        st.info(
            "Set GENE_EXPLORER_API_KEY to keep conversation history between "
            "questions. Without it each question is answered on its own.",
            icon="💬",
        )


def render_examples() -> None:
    st.write("**Try an example**")
    columns = st.columns(2)
    for index, question in enumerate(EXAMPLES):
        with columns[index % 2]:
            if st.button(question, key=f"example-{index}", use_container_width=True):
                st.session_state.pending = question


def render_history() -> None:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("tool_calls"):
                st.caption("Tools used: " + ", ".join(message["tool_calls"]))


def submit(question: str) -> None:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            reply = get_client().chat(question, session_id=st.session_state.session_id)
        if reply.ok:
            st.markdown(reply.answer)
            if reply.tool_calls:
                st.caption("Tools used: " + ", ".join(reply.tool_calls))
        else:
            st.warning(reply.answer, icon="⚠️")

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": reply.answer,
            "tool_calls": reply.tool_calls,
        }
    )


def main() -> None:
    init_state()
    render_header()

    if not st.session_state.messages:
        render_examples()
    else:
        if st.button("New conversation"):
            st.session_state.messages = []
            st.session_state.session_id = str(uuid.uuid4())
            st.rerun()

    render_history()

    question = st.chat_input("Ask about cancer genes…")
    if not question and st.session_state.pending:
        question = st.session_state.pending
        st.session_state.pending = None

    if question:
        submit(question)


main()

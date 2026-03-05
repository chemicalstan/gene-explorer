import os
# import requests
import streamlit as st
# import streamlit.components.v1 as components

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Gene Explorer", page_icon="🧬", layout="centered")

# ── Global styles ──────────────────────────────────────────────────────────────

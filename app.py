"""AI Market Research Analyst - Streamlit app powered by Claude."""
import os
from datetime import date

import anthropic
import streamlit as st

from prompts import DEPTH, MODES, SYSTEM_PROMPT, build_task_prompt

st.set_page_config(page_title="AI Market Research Analyst", page_icon="📊", layout="wide")

MODEL_OPTIONS = ["claude-sonnet-5-5", "claude-opus-5-5", "claude-haiku-5-5"]


def get_api_key():
    try:
        key = st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        key = None
    return key or os.environ.get("ANTHROPIC_API_KEY") or st.session_state.get("user_key")


def stream_claude(messages, model, use_search, max_tokens, api_key):
    client = anthropic.Anthropic(api_key=api_key)
    kwargs = dict(
        model=model,
        max_tokens=max_tokens,
        system=SYSTEM_PROMPT.replace("{today}", date.today().isoformat()),
        messages=[{"role": m["role"], "content": m["content"]} for m in messages],
    )
    if use_search:
        kwargs["tools"] = [{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}]
    with client.messages.stream(**kwargs) as stream:
        for text in stream.text_stream:
            yield text


if "messages" not in st.session_state:
    st.session_state.messages = []

# ---------- Sidebar ----------
with st.sidebar:
    st.header("⚙️ Settings")
    if not get_api_key():
        st.text_input("Anthropic API key", type="password", key="user_key",
                      help="Or add ANTHROPIC_API_KEY to Streamlit secrets.")
    model = st.selectbox("Model", MODEL_OPTIONS)
    use_search = st.toggle("🔎 Live web search", value=True,
                           help="Lets Claude pull current data and sources.")
    max_tokens = st.slider("Max output tokens", 1000, 8000, 4000, 500)
    if st.button("🗑️ Clear conversation"):
        st.session_state.messages = []
        st.rerun()
    st.caption("Research output is AI-generated. Verify key figures before decisions.")

st.title("📊 AI Market Research Analyst")
st.caption("Market size • Competitor analysis • Trends • Market reports")

# ---------- Request form ----------
with st.form("request"):
    c1, c2 = st.columns(2)
    mode = c1.selectbox("Analysis type", list(MODES.keys()), index=3)
    market = c2.text_input("Market / industry", placeholder="e.g. AI-powered customer support software")
    c3, c4, c5 = st.columns(3)
    region = c3.text_input("Geography", value="Global")
    timeframe = c4.text_input("Forecast horizon", value="2026-2031")
    depth = c5.selectbox("Depth", list(DEPTH.keys()), index=1)
    competitors = st.text_input("Competitors (optional)", placeholder="Comma-separated, e.g. Zendesk, Intercom, Freshworks")
    context = st.text_area("Extra context (optional)", placeholder="Your product, target customer, budget, goals...", height=80)
    submitted = st.form_submit_button("🚀 Generate research", type="primary")

# ---------- Run ----------
api_key = get_api_key()

if submitted:
    if not market.strip():
        st.warning("Please enter a market or industry.")
    elif not api_key:
        st.error("Add your Anthropic API key in the sidebar or Streamlit secrets.")
    else:
        prompt = build_task_prompt(mode, market, region, timeframe, competitors, context, depth)
        st.session_state.messages = [
            {"role": "user", "content": prompt, "display": f"**{mode}** - {market} ({region}, {timeframe})"}
        ]
        with st.chat_message("assistant"):
            try:
                text = st.write_stream(
                    stream_claude(st.session_state.messages, model, use_search, max_tokens, api_key)
                )
                st.session_state.messages.append({"role": "assistant", "content": text})
            except anthropic.APIError as e:
                st.error(f"API error: {e}")
        st.rerun()

# ---------- Conversation ----------
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m.get("display", m["content"]))

last = next((m for m in reversed(st.session_state.messages) if m["role"] == "assistant"), None)
if last:
    st.download_button("⬇️ Download report (.md)", last["content"],
                       file_name=f"market_report_{date.today().isoformat()}.md", mime="text/markdown")

    if follow := st.chat_input("Ask a follow-up (e.g. 'drill into the SMB segment')"):
        st.session_state.messages.append({"role": "user", "content": follow})
        with st.chat_message("user"):
            st.markdown(follow)
        with st.chat_message("assistant"):
            try:
                text = st.write_stream(
                    stream_claude(st.session_state.messages, model, use_search, max_tokens, api_key)
                )
                st.session_state.messages.append({"role": "assistant", "content": text})
            except anthropic.APIError as e:
                st.error(f"API error: {e}")
        st.rerun()

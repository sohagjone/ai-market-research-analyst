"""AI Market Research Analyst - Streamlit app."""
import os
from datetime import date

import anthropic
import streamlit as st
from google import genai
from google.genai import types

from prompts import DEPTH, MODES, SYSTEM_PROMPT, build_task_prompt

st.set_page_config(page_title="AI Market Research Analyst", page_icon="📊", layout="wide")

PROVIDERS = {
    "Google Gemini (FREE)": {
        "secret": "GEMINI_API_KEY",
        "models": ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-pro"],
    },
    "Anthropic Claude (paid)": {
        "secret": "ANTHROPIC_API_KEY",
        "models": ["claude-sonnet-5-5", "claude-opus-5-5", "claude-haiku-5-5"],
    },
}


def get_api_key(secret_name):
    try:
        key = st.secrets[secret_name]
    except Exception:
        key = None
    return key or os.environ.get(secret_name) or st.session_state.get("user_key")


def stream_gemini(messages, model, use_search, max_tokens, api_key):
    client = genai.Client(api_key=api_key)
    contents = [
        types.Content(role="user" if m["role"] == "user" else "model",
                      parts=[types.Part(text=m["content"])])
        for m in messages
    ]

    def run(with_search):
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT.replace("{today}", date.today().isoformat()),
            max_output_tokens=max_tokens,
            tools=[types.Tool(google_search=types.GoogleSearch())] if with_search else None,
        )
        for chunk in client.models.generate_content_stream(model=model, contents=contents, config=config):
            if chunk.text:
                yield chunk.text

    started = False
    try:
        for t in run(use_search):
            started = True
            yield t
    except Exception as e:
        if use_search and not started:
            yield "_Web search is unavailable on this key/model, continuing without it._\n\n"
            yield from run(False)
        else:
            raise


def stream_anthropic(messages, model, use_search, max_tokens, api_key):
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


def stream_llm(messages):
    cfg = st.session_state.cfg
    fn = stream_gemini if cfg["provider"].startswith("Google") else stream_anthropic
    return fn(messages, cfg["model"], cfg["use_search"], cfg["max_tokens"], cfg["api_key"])


if "messages" not in st.session_state:
    st.session_state.messages = []

# ---------- Sidebar ----------
with st.sidebar:
    st.header("⚙️ Settings")
    provider = st.selectbox("AI provider", list(PROVIDERS.keys()))
    secret_name = PROVIDERS[provider]["secret"]
    if not get_api_key(secret_name):
        st.text_input(f"{secret_name}", type="password", key="user_key",
                      help="Or add it to Streamlit secrets.")
        if provider.startswith("Google"):
            st.markdown("[Get a free Gemini key](https://aistudio.google.com/apikey)")
    model = st.selectbox("Model", PROVIDERS[provider]["models"])
    custom = st.text_input("Custom model name (optional)", help="Overrides the model above.")
    use_search = st.toggle("🔎 Live web search", value=True,
                           help="Google Search grounding (Gemini) or web search (Claude).")
    max_tokens = st.slider("Max output tokens", 1000, 8000, 4000, 500)
    if st.button("🗑️ Clear conversation"):
        st.session_state.messages = []
        st.rerun()
    st.caption("Research output is AI-generated. Verify key figures before decisions.")

st.session_state.cfg = dict(provider=provider, model=custom.strip() or model,
                            use_search=use_search, max_tokens=max_tokens,
                            api_key=get_api_key(secret_name))

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
api_key = st.session_state.cfg['api_key']

if submitted:
    if not market.strip():
        st.warning("Please enter a market or industry.")
    elif not api_key:
        st.error("Add your API key in the sidebar or Streamlit secrets.")
    else:
        prompt = build_task_prompt(mode, market, region, timeframe, competitors, context, depth)
        st.session_state.messages = [
            {"role": "user", "content": prompt, "display": f"**{mode}** - {market} ({region}, {timeframe})"}
        ]
        with st.chat_message("assistant"):
            try:
                text = st.write_stream(
                    stream_llm(st.session_state.messages)
                )
                st.session_state.messages.append({"role": "assistant", "content": text})
            except Exception as e:
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
                    stream_llm(st.session_state.messages)
                )
                st.session_state.messages.append({"role": "assistant", "content": text})
            except Exception as e:
                st.error(f"API error: {e}")
        st.rerun()

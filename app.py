"""AI Market Research Analyst - Streamlit app (free Gemini API or Claude)."""
import os
from datetime import date

import anthropic
import streamlit as st
from google import genai
from google.genai import types

from prompts import DEPTH, MODES, SYSTEM_PROMPT, build_task_prompt

st.set_page_config(page_title="AI Market Research Analyst", page_icon="📊", layout="wide")

GEMINI_MODELS = ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-3.8-flash", "gemini-2.5-flash"]

PROVIDERS = {
    "Google Gemini (FREE)": {
        "secret": "GEMINI_API_KEY",
        "models": GEMINI_MODELS,
    },
    "Anthropic Claude (paid)": {
        "secret": "ANTHROPIC_API_KEY",
        "models": ["claude-sonnet-5-5", "claude-opus-5-5", "claude-haiku-5-5"],
    },
}

for k, v in {"messages": [], "pending": False, "error": None}.items():
    st.session_state.setdefault(k, v)


def system_prompt():
    return SYSTEM_PROMPT.replace("{today}", date.today().isoformat())


def get_api_key(secret_name):
    try:
        key = st.secrets[secret_name]
    except Exception:
        key = None
    return key or os.environ.get(secret_name) or st.session_state.get("user_key")


# ---------------------------------------------------------------- Gemini
def _text_of(resp):
    """Extract text from a Gemini response/chunk without raising."""
    try:
        if resp.text:
            return resp.text
    except Exception:
        pass
    out = []
    try:
        for cand in resp.candidates or []:
            for part in (cand.content.parts or []) if cand.content else []:
                if getattr(part, "text", None) and not getattr(part, "thought", False):
                    out.append(part.text)
    except Exception:
        pass
    return "".join(out)


def stream_gemini(messages, model, use_search, max_tokens, api_key):
    client = genai.Client(api_key=api_key)
    contents = [
        types.Content(role="user" if m["role"] == "user" else "model",
                      parts=[types.Part(text=m["content"])])
        for m in messages
    ]

    def config(search, thinking_off):
        thinking = None
        if thinking_off and "2.5" in model and "pro" not in model:
            thinking = types.ThinkingConfig(thinking_budget=0)
        return types.GenerateContentConfig(
            system_instruction=system_prompt(),
            max_output_tokens=max_tokens,
            thinking_config=thinking,
            tools=[types.Tool(google_search=types.GoogleSearch())] if search else None,
        )

    attempts = [(use_search, True)]
    if use_search:
        attempts.append((False, True))
    attempts.append((False, False))

    errors = []
    for search, thinking_off in attempts:
        got, finish = False, None
        try:
            for chunk in client.models.generate_content_stream(
                    model=model, contents=contents, config=config(search, thinking_off)):
                if chunk.candidates and chunk.candidates[0].finish_reason:
                    finish = str(chunk.candidates[0].finish_reason)
                txt = _text_of(chunk)
                if txt:
                    got = True
                    yield txt
            if got:
                if finish and "MAX_TOKENS" in finish:
                    yield ("\n\n---\n⚠️ **The report hit the token limit and was cut off.** "
                           "Type `continue` below or raise *Max output tokens*.")
                if not search and use_search:
                    yield "\n\n_(Web search was unavailable, so this report has no live data.)_"
                return
            # Stream gave nothing: try a normal (non-streaming) call
            resp = client.models.generate_content(
                model=model, contents=contents, config=config(search, thinking_off))
            txt = _text_of(resp)
            if txt:
                yield txt
                return
            errors.append(f"[search={search}] Empty response. finish_reason={finish}, "
                          f"feedback={getattr(resp, 'prompt_feedback', None)}")
        except Exception as e:
            if got:
                raise
            errors.append(f"[search={search}, thinking_off={thinking_off}] {type(e).__name__}: {e}")
    raise RuntimeError("Gemini returned no report.\n\n" + "\n\n".join(errors))


def stream_gemini_auto(messages, model, use_search, max_tokens, api_key):
    """Try the chosen model; if Google says it no longer exists (404), try the next one."""
    candidates = [model] + [m for m in GEMINI_MODELS if m != model]
    tried = []
    for m in candidates:
        got = False
        try:
            if m != model:
                yield f"_`{model}` is not available, using `{m}` instead._\n\n"
            for t in stream_gemini(messages, m, use_search, max_tokens, api_key):
                got = True
                yield t
            return
        except Exception as e:
            msg = str(e)
            if got or not ("NOT_FOUND" in msg or "404" in msg):
                raise
            tried.append(m)
    raise RuntimeError("None of these Gemini models are available to your key: " + ", ".join(tried))


# ---------------------------------------------------------------- Claude
def stream_anthropic(messages, model, use_search, max_tokens, api_key):
    client = anthropic.Anthropic(api_key=api_key)
    kwargs = dict(
        model=model, max_tokens=max_tokens, system=system_prompt(),
        messages=[{"role": m["role"], "content": m["content"]} for m in messages],
    )
    if use_search:
        kwargs["tools"] = [{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}]
    with client.messages.stream(**kwargs) as stream:
        for text in stream.text_stream:
            yield text


def stream_llm(messages):
    cfg = st.session_state.cfg
    fn = stream_gemini_auto if cfg["provider"].startswith("Google") else stream_anthropic
    return fn(messages, cfg["model"], cfg["use_search"], cfg["max_tokens"], cfg["api_key"])


# ---------------------------------------------------------------- Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    provider = st.selectbox("AI provider", list(PROVIDERS.keys()))
    secret_name = PROVIDERS[provider]["secret"]
    if not get_api_key(secret_name):
        st.text_input(secret_name, type="password", key="user_key",
                      help="Or add it to Streamlit secrets.")
        if provider.startswith("Google"):
            st.markdown("[Get a free Gemini key](https://aistudio.google.com/apikey)")
    model = st.selectbox("Model", PROVIDERS[provider]["models"])
    custom = st.text_input("Custom model name (optional)", help="Overrides the model above.")
    use_search = st.toggle("🔎 Live web search", value=False,
                           help="Turn on after the basic report works. May not be available on free keys.")
    max_tokens = st.slider("Max output tokens", 2000, 32000, 12000, 1000)

    cfg = dict(provider=provider, model=custom.strip() or model, use_search=use_search,
               max_tokens=max_tokens, api_key=get_api_key(secret_name))
    st.session_state.cfg = cfg

    if st.button("🧪 Test API connection"):
        if not cfg["api_key"]:
            st.error("No API key found.")
        else:
            try:
                reply = "".join(stream_gemini_auto([{"role": "user", "content": "Reply with the word OK."}],
                                              cfg["model"], False, 200, cfg["api_key"])) \
                    if provider.startswith("Google") else "".join(
                        stream_anthropic([{"role": "user", "content": "Reply with the word OK."}],
                                         cfg["model"], False, 200, cfg["api_key"]))
                st.success(f"Connected. Model replied: {reply.strip()[:60]}")
            except Exception as e:
                st.error(f"{type(e).__name__}: {e}")

    if st.button("🗑️ Clear conversation"):
        st.session_state.update(messages=[], pending=False, error=None)
        st.rerun()
    st.caption("Research output is AI-generated. Verify key figures before decisions.")

# ---------------------------------------------------------------- Main
st.title("📊 AI Market Research Analyst")
st.caption("Market size • Competitor analysis • Trends • Market reports")

with st.form("request"):
    c1, c2 = st.columns(2)
    mode = c1.selectbox("Analysis type", list(MODES.keys()), index=3)
    market = c2.text_input("Market / industry", placeholder="e.g. AI-powered customer support software")
    c3, c4, c5 = st.columns(3)
    region = c3.text_input("Geography", value="Global")
    timeframe = c4.text_input("Forecast horizon", value="2026-2031")
    depth = c5.selectbox("Depth", list(DEPTH.keys()), index=1)
    competitors = st.text_input("Competitors (optional)", placeholder="Comma-separated, e.g. Zendesk, Intercom")
    context = st.text_area("Extra context (optional)", placeholder="Your product, target customer, goals...", height=80)
    submitted = st.form_submit_button("🚀 Generate research", type="primary")

if submitted:
    if not market.strip():
        st.warning("Please enter a market or industry.")
    elif not cfg["api_key"]:
        st.error("Add your API key in the sidebar or Streamlit secrets.")
    else:
        prompt = build_task_prompt(mode, market, region, timeframe, competitors, context, depth)
        st.session_state.messages = [
            {"role": "user", "content": prompt, "display": f"**{mode}** - {market} ({region}, {timeframe})"}
        ]
        st.session_state.pending = True
        st.session_state.error = None

# Show conversation so far
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m.get("display", m["content"]))

# Generate (runs after the history is drawn, so output appears at the bottom)
if st.session_state.pending:
    st.session_state.pending = False
    with st.chat_message("assistant"):
        try:
            with st.spinner("Researching... this can take 30-90 seconds"):
                text = st.write_stream(stream_llm(st.session_state.messages))
            if not text or not str(text).strip():
                raise RuntimeError("The model returned an empty response.")
            st.session_state.messages.append({"role": "assistant", "content": str(text)})
            st.rerun()
        except Exception as e:
            if type(e).__name__ in ("RerunException", "StopException"):
                raise
            st.session_state.error = f"{type(e).__name__}: {e}"

# Errors persist on screen (they are no longer wiped by a rerun)
if st.session_state.error:
    st.error(st.session_state.error)
    st.info("Tips: turn **Live web search** off, click **Test API connection** in the sidebar, "
            "or try another model name. A 429 / RESOURCE_EXHAUSTED error means the free daily quota is used up.")

last = next((m for m in reversed(st.session_state.messages) if m["role"] == "assistant"), None)
if last:
    st.download_button("⬇️ Download report (.md)", last["content"],
                       file_name=f"market_report_{date.today().isoformat()}.md", mime="text/markdown")

if st.session_state.messages and not st.session_state.pending:
    if follow := st.chat_input("Ask a follow-up (e.g. 'drill into the SMB segment' or 'continue')"):
        st.session_state.messages.append({"role": "user", "content": follow})
        st.session_state.pending = True
        st.session_state.error = None
        st.rerun()

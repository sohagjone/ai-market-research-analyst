"""AI Market Research Analyst - Streamlit app (free Gemini API or Claude)."""
import os
import re
from datetime import date

import anthropic
import streamlit as st
from google import genai
from google.genai import types

import exporters
from prompts import DEPTH, MODES, SYSTEM_PROMPT, build_task_prompt

st.set_page_config(page_title="AI Market Research Analyst", page_icon="📊", layout="wide")

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"], .stMarkdown, button, input, textarea { font-family: 'Inter', sans-serif !important; }
.stApp { background: linear-gradient(180deg, #F6F7FF 0%, #FFFFFF 40%); }
footer { visibility: hidden; }
.block-container { padding-top: 2rem; max-width: 1150px; }

/* Hero */
.hero { background: linear-gradient(120deg, #4F46E5 0%, #7C3AED 45%, #EC4899 100%); border-radius: 24px;
  padding: 2.2rem 2.4rem; color: #fff; box-shadow: 0 18px 40px rgba(79,70,229,.28); position: relative; overflow: hidden; }
.hero:before { content:""; position:absolute; right:-60px; top:-60px; width:240px; height:240px; border-radius:50%;
  background: rgba(255,255,255,.12); }
.hero:after { content:""; position:absolute; right:120px; bottom:-90px; width:200px; height:200px; border-radius:50%;
  background: rgba(245,158,11,.35); }
.hero h1 { color:#fff !important; font-size: 2.3rem; font-weight: 800; margin: .3rem 0 .4rem 0; padding: 0; }
.hero p { color: #E0E7FF; font-size: 1.05rem; margin: 0 0 1rem 0; max-width: 720px; }
.badge { display:inline-block; background: rgba(255,255,255,.2); border:1px solid rgba(255,255,255,.35);
  padding: .2rem .8rem; border-radius: 999px; font-size: .72rem; font-weight: 700; letter-spacing: .08em; }
.chip { display:inline-block; background:#fff; color:#4F46E5; border-radius: 999px; padding:.3rem .9rem;
  font-size:.82rem; font-weight:600; margin: 0 .4rem .4rem 0; position: relative; z-index: 1; }

/* Feature cards */
.cards { display:grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin: 1.4rem 0 .6rem 0; }
.card { background:#fff; border-radius:18px; padding:1.2rem; border:1px solid #E5E7FB; border-top-width:5px;
  box-shadow:0 8px 24px rgba(31,35,64,.06); }
.card .ico { font-size: 1.8rem; }
.card h4 { margin:.4rem 0 .2rem 0; font-size:1rem; color:#1F2340; }
.card p { margin:0; font-size:.85rem; color:#6B7280; line-height:1.4; }
@media (max-width: 900px) { .cards { grid-template-columns: repeat(2, 1fr); } }

/* Form */
[data-testid="stForm"] { background:#fff; border:1px solid #E5E7FB; border-radius:20px; padding:1.4rem 1.6rem;
  box-shadow:0 10px 32px rgba(79,70,229,.08); }
[data-testid="stFormSubmitButton"] button { background: linear-gradient(90deg,#4F46E5,#EC4899); color:#fff; border:0;
  border-radius:12px; font-weight:700; padding:.7rem 1.8rem; box-shadow:0 8px 20px rgba(236,72,153,.3); }
[data-testid="stFormSubmitButton"] button:hover { transform: translateY(-1px); filter: brightness(1.05); color:#fff; }

/* Sidebar */
[data-testid="stSidebar"] { background: linear-gradient(180deg, #EEF0FF 0%, #FDF2F8 100%); border-right:1px solid #E5E7FB; }
[data-testid="stSidebar"] .stButton button { border-radius:10px; border:1px solid #C7D2FE; background:#fff; font-weight:600; }

/* Chat / report card */
[data-testid="stChatMessage"] { background:#fff; border:1px solid #E5E7FB; border-radius:18px; padding:1.1rem 1.3rem;
  box-shadow:0 8px 24px rgba(31,35,64,.06); margin-bottom: 1rem; }
[data-testid="stChatMessage"] h2 { color:#4F46E5; border-bottom:3px solid #EC4899; padding-bottom:.3rem; font-weight:800; font-size:1.45rem; }
[data-testid="stChatMessage"] h3 { color:#7C3AED; font-weight:700; }
[data-testid="stChatMessage"] table { border-collapse: collapse; width:100%; border-radius:10px; overflow:hidden; }
[data-testid="stChatMessage"] th { background: linear-gradient(90deg,#4F46E5,#7C3AED); color:#fff !important; padding:.55rem .7rem; }
[data-testid="stChatMessage"] td { padding:.5rem .7rem; border-bottom:1px solid #EEF0FF; }
[data-testid="stChatMessage"] tr:nth-child(even) td { background:#F6F7FF; }

/* Download panel */
.dl-head { background: linear-gradient(90deg,#14B8A6,#3B82F6); color:#fff; border-radius:16px; padding:1rem 1.3rem;
  margin: 1.2rem 0 .8rem 0; box-shadow:0 8px 20px rgba(20,184,166,.25); }
.dl-head b { font-size:1.1rem; } .dl-head span { opacity:.9; font-size:.88rem; display:block; }
[data-testid="stDownloadButton"] button { color:#fff !important; border:0; border-radius:14px; font-weight:700;
  padding:.8rem 1rem; width:100%; box-shadow:0 8px 18px rgba(31,35,64,.18); }
[data-testid="stDownloadButton"] button:hover { transform: translateY(-2px); filter:brightness(1.08); color:#fff; }
.st-key-dl_docx button { background: linear-gradient(135deg,#2B579A,#3B82F6); }
.st-key-dl_xlsx button { background: linear-gradient(135deg,#107C41,#10B981); }
.st-key-dl_pptx button { background: linear-gradient(135deg,#D24726,#F59E0B); }
.st-key-dl_pdf  button { background: linear-gradient(135deg,#E11D48,#EC4899); }
.st-key-dl_md   button { background: linear-gradient(135deg,#475569,#7C3AED); }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

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

for k, v in {"messages": [], "pending": False, "error": None, "meta": {}}.items():
    st.session_state.setdefault(k, v)


def system_prompt():
    return SYSTEM_PROMPT.replace("{today}", date.today().isoformat())


def get_api_key(secret_name):
    try:
        key = st.secrets[secret_name]
    except Exception:
        key = None
    return key or os.environ.get(secret_name) or st.session_state.get("user_key")



def md_safe(text):
    """Escape dollar signs so prices like $55-$169 are not rendered as math."""
    return text.replace("\\$", "$").replace("$", "\\$")


def stream_markdown(gen):
    """Stream chunks into the page and return the full text."""
    box, acc = st.empty(), ""
    for chunk in gen:
        acc += chunk
        box.markdown(md_safe(acc) + " ▌")
    box.markdown(md_safe(acc))
    return acc


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
st.markdown("""
<div class="hero">
  <span class="badge">AI POWERED</span>
  <h1>📊 AI Market Research Analyst</h1>
  <p>Professional market research in minutes: market size, competitor analysis, trends and executive-ready reports.</p>
  <span class="chip">📈 Market Size</span><span class="chip">🏢 Competitors</span>
  <span class="chip">🔥 Trends</span><span class="chip">📑 Full Reports</span>
</div>
""", unsafe_allow_html=True)

if not st.session_state.messages:
    st.markdown("""
    <div class="cards">
      <div class="card" style="border-top-color:#4F46E5"><div class="ico">📈</div><h4>Market Size</h4>
        <p>TAM / SAM / SOM with Low, Base and High scenarios and clear assumptions.</p></div>
      <div class="card" style="border-top-color:#EC4899"><div class="ico">🏢</div><h4>Competitor Analysis</h4>
        <p>Profiles, pricing, strengths, weaknesses and white-space opportunities.</p></div>
      <div class="card" style="border-top-color:#F59E0B"><div class="ico">🔥</div><h4>Trend Analysis</h4>
        <p>Emerging trends ranked by impact, maturity and time horizon.</p></div>
      <div class="card" style="border-top-color:#14B8A6"><div class="ico">📥</div><h4>Export Anywhere</h4>
        <p>Download as Word, Excel, PowerPoint or PDF with one click.</p></div>
    </div>
    """, unsafe_allow_html=True)

st.write("")
with st.form("request"):
    st.markdown("#### 🎯 Define your research")
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
        st.session_state.meta = {"title": f"{market.strip().title()}: {mode.split(' (')[0]}",
                                 "subtitle": f"{region}  |  {timeframe}"}
        st.session_state.pending = True
        st.session_state.error = None

# Show conversation so far
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(md_safe(m.get("display", m["content"])))

# Generate (runs after the history is drawn, so output appears at the bottom)
if st.session_state.pending:
    st.session_state.pending = False
    with st.chat_message("assistant"):
        try:
            with st.spinner("Researching... this can take 30-90 seconds"):
                text = stream_markdown(stream_llm(st.session_state.messages))
            if not text or not str(text).strip():
                raise RuntimeError("The model returned an empty response.")
            st.session_state.messages.append({"role": "assistant", "content": str(text)})
            st.rerun()
        except Exception as e:
            if type(e).__name__ in ("RerunException", "StopException"):
                raise
            st.session_state.error = f"{type(e).__name__}: {e}"

if st.session_state.error:
    st.error(st.session_state.error)
    st.info("Tips: turn **Live web search** off, click **Test API connection** in the sidebar, "
            "or try another model name. A 429 / RESOURCE_EXHAUSTED error means the free daily quota is used up.")


# ---------------------------------------------------------------- Downloads
def export_text():
    parts = [m["content"] for m in st.session_state.messages if m["role"] == "assistant"]
    text = "\n\n".join(parts)
    text = re.sub(r"\n*---\n⚠️[^\n]*", "", text)
    text = re.sub(r"^_`[^\n]*instead\._\s*", "", text, flags=re.M)
    return text


@st.cache_data(show_spinner=False)
def build_exports(report, title, subtitle):
    return exporters.build_all(report, title, subtitle)


if any(m["role"] == "assistant" for m in st.session_state.messages):
    report = export_text()
    meta = st.session_state.meta or {}
    title = meta.get("title", "Market Research Report")
    subtitle = meta.get("subtitle", "")
    files, errors = build_exports(report, title, subtitle)
    base = re.sub(r"[^A-Za-z0-9]+", "_", title).strip("_")[:40] or "market_report"

    st.markdown('<div class="dl-head"><b>📥 Download your report</b>'
                '<span>Pick the format you need. Files are styled and ready to share.</span></div>',
                unsafe_allow_html=True)
    formats = [
        ("docx", "📝 Word (.docx)", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ("xlsx", "📊 Excel (.xlsx)", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        ("pptx", "🎞️ PowerPoint (.pptx)", "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
        ("pdf", "📕 PDF (.pdf)", "application/pdf"),
    ]
    cols = st.columns(5)
    for col, (ext, label, mime) in zip(cols, formats):
        with col:
            if ext in files:
                st.download_button(label, files[ext], file_name=f"{base}.{ext}", mime=mime, key=f"dl_{ext}", use_container_width=True)
            else:
                st.button(f"{label} unavailable", disabled=True, key=f"na_{ext}", help=errors.get(ext), use_container_width=True)
    with cols[4]:
        st.download_button("🗒️ Markdown (.md)", report, file_name=f"{base}.md", mime="text/markdown", key="dl_md", use_container_width=True)
    for ext, err in errors.items():
        st.caption(f"⚠️ {ext.upper()} export failed: {err}")

if st.session_state.messages and not st.session_state.pending:
    if follow := st.chat_input("Ask a follow-up (e.g. 'drill into the SMB segment' or 'continue')"):
        st.session_state.messages.append({"role": "user", "content": follow})
        st.session_state.pending = True
        st.session_state.error = None
        st.rerun()

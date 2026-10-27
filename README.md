# 📊 AI Market Research Analyst

A Streamlit app powered by Claude that produces **market size estimates, competitor analyses,
trend reports, and full market research reports**, with optional live web search and cited sources.

## Features
- 4 analysis modes: Market Size, Competitor Analysis, Trend Analysis, Full Report
- Live web search (Anthropic web search tool) for current data
- Streaming output, follow-up questions, Markdown report download
- Low/Base/High market-size scenarios with stated assumptions

## Run locally
```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # add your key
streamlit run app.py
```

## Deploy to share.streamlit.io
1. Push this folder to a GitHub repo.
2. Go to https://share.streamlit.io -> **Create app** -> pick the repo, branch `main`, file `app.py`.
3. **Advanced settings -> Secrets**, add: `ANTHROPIC_API_KEY = "sk-ant-..."`
4. Deploy.

> Never commit your real API key. `.streamlit/secrets.toml` is git-ignored.
> Get a key at https://console.anthropic.com. If a model name errors, update `MODEL_OPTIONS` in `app.py`.

## Structure
```
app.py                    # Streamlit UI + Claude streaming
prompts.py                # System prompt + task templates (edit to tune the analyst)
claude_project_prompt.md  # Same prompt for a Claude.ai Project
requirements.txt
.streamlit/
```

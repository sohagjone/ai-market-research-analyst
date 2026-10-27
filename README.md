# 📊 AI Market Research Analyst

A Streamlit app that runs on a **free Google Gemini API key** (or Claude, optional) and produces **market size estimates, competitor analyses,
trend reports, and full market research reports**, with optional live web search and cited sources.

## Features
- 4 analysis modes: Market Size, Competitor Analysis, Trend Analysis, Full Report
- Free Gemini API support, with optional Claude
- Live web search (Google Search grounding) when your key allows it; falls back automatically
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
3. **Advanced settings -> Secrets**, add: `GEMINI_API_KEY = "AIza..."` (free key from https://aistudio.google.com/apikey)
4. Deploy.

> Never commit your real API key. `.streamlit/secrets.toml` is git-ignored.
> Free-tier limits and model availability change often. Check your limits at https://aistudio.google.com/rate-limit. If a model name errors, type another into the **Custom model name** box in the sidebar.

## Structure
```
app.py                    # Streamlit UI + Claude streaming
prompts.py                # System prompt + task templates (edit to tune the analyst)
claude_project_prompt.md  # Same prompt for a Claude.ai Project
requirements.txt
.streamlit/
```

# 🎯 CallIQ — AI-Powered Customer Support Quality Auditor

> **GenAI-powered quality auditing platform** that reviews customer support calls and chat transcripts, assigns quality scores, detects compliance violations, and suggests improvements in real time.

---

## 🚀 Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/sirishachoppara-77/GenAI-Powered-Customer-SupportQuality-Auditor.git
cd GenAI-Powered-Customer-SupportQuality-Auditor

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
python -m streamlit run app.py
```

Open **http://localhost:8501** in your browser.

> **No API keys?** The app runs in full **demo mode** with mock transcription and evaluation — all features work without any keys.

---

## 📁 Project Structure

```
├── app.py                  # Main Streamlit application (5 tabs)
├── rag_engine.py           # RAG pipeline — policy doc ingestion, FAISS vector store, audit
├── alerts.py               # Compliance alerting — Email, Slack, Teams
├── report_exporter.py      # PDF & Excel audit report generation
├── call_transcriber.py     # Batch CLI — M4A audio → transcript → summary JSON
├── chat_summarizer.py      # Batch CLI — chat logs → summary .txt via Groq
├── requirements.txt        # Python dependencies
├── Procfile                # Deployment config (Render / Railway)
├── license.txt             # MIT License
├── policy_docs/            # Policy documents for RAG auditing (auto-created)
└── .streamlit/
    └── config.toml         # Streamlit theme config
```

---

## 🧠 How It Works

```
Upload File (.txt / audio / video)
        │
        ├── .txt ──────────────────────────────────► LLM Evaluation
        │
        └── Audio / Video
                │
                ├── Audio ──► Deepgram API ──► Transcript ──► LLM Evaluation
                │
                └── Video ──► moviepy (extract audio) ──► Deepgram ──► LLM Evaluation
                                                                    │
                                                    ┌───────────────┴───────────────┐
                                                    ▼                               ▼
                                            5-Dimension Scores            RAG Policy Audit
                                            Compliance Flags              (FAISS + policy docs)
                                            Improvement Suggestions
                                                    │
                                        ┌───────────┴───────────┐
                                        ▼                       ▼
                                Alerts (Email/Slack/Teams)   Export (.txt / .pdf / .xlsx)
```

---

## 📊 Scoring System

Each call is scored across **5 dimensions** (0–5 each), totalling **0–25**:

| Dimension | Description |
|-----------|-------------|
| 👋 Greeting Quality | Warmth, professionalism, proper introduction |
| ❤️ Empathy | Acknowledging feelings, genuine human connection |
| 🔍 Problem Understanding | Active listening, correct issue diagnosis |
| ✅ Resolution Clarity | Clear solution, actionable next steps |
| 💼 Professionalism | Language quality, composure, brand voice |

**Grade**: A (≥90%) · B (≥75%) · C (≥60%) · D (≥50%) · F (<50%)

---

## 🖥️ App Tabs

| Tab | Description |
|-----|-------------|
| 🎧 **Analyze** | Upload file → transcribe → evaluate → radar chart + scores + suggestions + export |
| 📈 **History & Trends** | Score trend graph, evaluation history CSV, summary stats |
| 🔍 **Policy RAG Audit** | Upload policy docs → FAISS index → policy-grounded compliance audit |
| 🔔 **Alerts & Reports** | Configure thresholds, Email/Slack/Teams alerts, export PDF/Excel |
| ℹ️ **About** | How it works, API config guide, scoring reference |

---

## 🔑 API Keys

| Key | Purpose | Get it at |
|-----|---------|-----------|
| `DEEPGRAM_API_KEY` | Speech-to-text transcription | [deepgram.com](https://deepgram.com) |
| `OPENROUTER_API_KEY` | LLM evaluation + RAG audit (GPT-4o-mini) | [openrouter.ai](https://openrouter.ai) |
| `OPENAI_API_KEY` | Embeddings for RAG pipeline (optional) | [platform.openai.com](https://platform.openai.com) |

### Set as environment variables (recommended)

**Windows PowerShell:**
```powershell
$env:DEEPGRAM_API_KEY    = "your_key_here"
$env:OPENROUTER_API_KEY  = "your_key_here"
```

**macOS / Linux:**
```bash
export DEEPGRAM_API_KEY="your_key_here"
export OPENROUTER_API_KEY="your_key_here"
```

> Keys can also be hardcoded directly in the scripts for local development.

---

## 🔍 RAG Policy Audit (Milestone 3)

The RAG (Retrieval-Augmented Generation) pipeline audits calls against **your company's own policy documents**:

1. Upload `.txt`, `.md`, or `.pdf` policy files via the Policy RAG Audit tab
2. Click **Build Index** — documents are chunked, embedded, and stored in a FAISS vector index
3. Run a policy audit on any transcript — the system retrieves the most relevant policy sections and generates grounded feedback

**Works offline** — TF-IDF fallback embedder and SimpleVectorStore require no API keys or external dependencies.

---

## 🔔 Compliance Alerting (Milestone 4)

Automatic alerts fire when evaluations cross configurable thresholds:

- Score below threshold (default: 10/25)
- High escalation risk detected
- Any compliance violation detected
- Critical keywords found (lawsuit, fraud, data breach, etc.)
- Negative sentiment + low score

**Notification channels:** Email (SMTP), Slack (webhook), Microsoft Teams (webhook)

All triggered alerts are logged to `calliq_alerts.json` and viewable in the Alerts tab.

---

## 📄 Report Export (Milestone 4)

After every analysis, download the audit report in three formats:

| Format | Contents |
|--------|----------|
| `.txt` | Full text report — scores, violations, suggestions, transcript |
| `.pdf` | Professional formatted report with colour-coded tables (ReportLab) |
| `.xlsx` | 4-sheet Excel — Summary, Score Chart, Compliance & Suggestions, Full Transcript |

---

## 🖥️ Batch Processing (CLI Scripts)

### Transcribe & summarize call recordings

```bash
python call_transcriber.py call1.m4a call2.m4a
# Output: call_summaries.json
```

### Summarize chat logs

```bash
python chat_summarizer.py human_chat.txt
# Output: human_chat_summary.txt
```

---

## 🚀 Deployment

### Streamlit Cloud (recommended, free)

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) → New app
3. Select your repo, set `app.py` as the entry point
4. Add API keys under **Settings → Secrets**:
```toml
DEEPGRAM_API_KEY = "your_key"
OPENROUTER_API_KEY = "your_key"
```
5. Click **Deploy**

### Render.com

1. Connect your GitHub repo
2. New Web Service → `python` environment
3. The `Procfile` handles the start command automatically
4. Add API keys as environment variables

---

## 📦 Milestones

| Milestone | Weeks | Status | Deliverables |
|-----------|-------|--------|-------------|
| M1 — Transcription | 1–2 | ✅ Complete | `call_transcriber.py`, `chat_summarizer.py`, Deepgram + Groq integration |
| M2 — LLM Scoring | 3–4 | ✅ Complete | 5-dimension scoring engine, compliance detection, Streamlit UI |
| M3 — RAG & Dashboard | 5–6 | ✅ Complete | `rag_engine.py`, FAISS vector store, Policy RAG Audit tab, History tab |
| M4 — Alerts & Deploy | 7–8 | ✅ Complete | `alerts.py`, `report_exporter.py`, Email/Slack/Teams, PDF/Excel export |

---

## ⚠️ Responsible AI Notice

AI evaluations are **assistive tools** to support — not replace — human judgment. Scores should never be the sole basis for employment, disciplinary, or compensation decisions. Always combine AI insights with human review.

---

## 📜 License

MIT License — Copyright (c) 2026 Vidzai Digital

See [license.txt](license.txt) for full terms.

---

## 👤 Author: Sirisha Choppara

**Sirisha Choppara** · Vidzai Digital

Project: GenAI-Powered Customer Support Quality Auditor

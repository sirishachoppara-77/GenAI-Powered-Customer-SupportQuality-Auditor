# Chat / Log Summarizer

Summarizes any chat or log file into 1-2 sentences using the Groq API (free & fast).

## Usage

```bash
python chat_summarizer.py <file_path>
```

**Example:**
```bash
python chat_summarizer.py human_chat.txt
```

**Output:**
- Prints the summary in the terminal
- Saves `<filename>_summary.txt` in the same folder as the input file

## Supported File Types

`.txt` `.log` `.csv` `.json` `.md`

## Setup

**1. Install dependencies**
```bash
pip install -r requirements.txt
```

**2. Get a free Groq API key**
- Go to [https://console.groq.com](https://console.groq.com)
- Sign up → API Keys → Create API Key
- Copy the key (starts with `gsk_...`)

**3. Paste your key in `chat_summarizer.py`**
```python
GROQ_API_KEY = "gsk_your_key_here"
```

**4. Run**
```bash
python chat_summarizer.py human_chat.txt
```

## Models Used (in fallback order)

| Model | Context |
|-------|---------|
| llama-3.1-8b-instant | 12,000 chars |
| llama-3.3-70b-versatile | 6,000 chars |
| gemma2-9b-it | 6,000 chars |
| mixtral-8x7b-32768 | 6,000 chars |

If one model fails, the next is tried automatically.

## Groq Free Tier Limits

- **14,400 requests/day** on llama-3.1-8b-instant
- No credit card required
- Sign up at [console.groq.com](https://console.groq.com)

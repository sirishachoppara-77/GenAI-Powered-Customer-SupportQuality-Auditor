"""
Chat/Log Summarizer using Groq API
Usage: python chat_summarizer.py <file_path>
"""

import json
import sys
from pathlib import Path

GROQ_API_KEY = "YOUR_GROQ_API_KEY"

# Groq free tier limits per model (context tokens)
MODELS = [
    ("llama-3.1-8b-instant",    12_000),   # fast, large context
    ("llama-3.3-70b-versatile",  6_000),   # smart, smaller limit on free
    ("gemma2-9b-it",             6_000),
    ("mixtral-8x7b-32768",       6_000),
]

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}


def read_file(file_path: str) -> str:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def chunk_for_model(content: str, max_chars: int) -> str:
    """Keep beginning + end, skip middle if too large."""
    if len(content) <= max_chars:
        return content
    half = max_chars // 2
    return (
        content[:half]
        + "\n\n[...middle omitted for length...]\n\n"
        + content[-half:]
    )


def call_groq(content: str, model: str, max_chars: int) -> str:
    import requests
    chunked = chunk_for_model(content, max_chars)
    payload = {
        "model": model,
        "max_tokens": 150,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a precise summarizer. "
                    "Read the chat or log content and respond with ONLY "
                    "1-2 sentences that capture the core topic or outcome. "
                    "No bullet points, no extra commentary."
                ),
            },
            {
                "role": "user",
                "content": f"Summarize this chat in 1-2 sentences:\n\n{chunked}",
            },
        ],
    }

    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=HEADERS,
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()
    result = resp.json()
    choices = result.get("choices", [])
    if not choices:
        raise RuntimeError("Empty response")
    text = choices[0].get("message", {}).get("content", "").strip()
    if not text:
        raise RuntimeError("Empty content")
    return text


def save_summary(input_path: str, summary: str) -> str:
    path = Path(input_path).resolve()
    out_path = path.parent / (path.stem + "_summary.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(summary + "\n")
    return str(out_path)


def main():
    if len(sys.argv) < 2:
        print("Usage: python chat_summarizer.py <file_path>")
        sys.exit(1)

    file_path = sys.argv[1]

    try:
        content = read_file(file_path)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)

    summary = None
    for model, max_chars in MODELS:
        try:
            summary = call_groq(content, model, max_chars)
            break
        except Exception as e:
            print(f"  [{model}] failed: {e}", file=sys.stderr)
            continue

    if not summary:
        print("All models failed.")
        sys.exit(1)

    out_path = save_summary(file_path, summary)
    print(summary)
    print(f"\nSaved to: {out_path}")


if __name__ == "__main__":
    main()

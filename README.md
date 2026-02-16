# Call Log Transcription & Summarization Script

A Python script that processes M4A call recordings by:
1. Transcribing audio using Deepgram API
2. Summarizing transcriptions using OpenRouter's OpenAI LLM
3. Outputting clean, two-line summaries

## Prerequisites

- Python 3.8+
- Deepgram API key ([Get one here](https://deepgram.com/))
- OpenRouter API key ([Get one here](https://openrouter.ai/))

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up your API keys as environment variables:
```bash
export DEEPGRAM_API_KEY='your_deepgram_api_key_here'
export OPENROUTER_API_KEY='your_openrouter_api_key_here'
```

Or add them to your `~/.bashrc` or `~/.zshrc`:
```bash
echo 'export DEEPGRAM_API_KEY="your_key_here"' >> ~/.bashrc
echo 'export OPENROUTER_API_KEY="your_key_here"' >> ~/.bashrc
source ~/.bashrc
```

## Usage

Process a single call:
```bash
python call_transcriber.py call_recording.m4a
```

Process multiple calls:
```bash
python call_transcriber.py call1.m4a call2.m4a call3.m4a
```

## Output

The script provides:
- Console output with transcription preview and summary
- A `call_summaries.json` file containing all transcripts and summaries

### Example Output

```
============================================================
Processing: customer_call_2024.m4a
============================================================

Step 1: Transcribing audio with Deepgram...
✓ Transcription complete (1234 characters)

Transcript preview:
Hello, this is John from customer support. How can I help you today...

Step 2: Summarizing with OpenRouter OpenAI LLM...
✓ Summary complete

============================================================
SUMMARY:
============================================================
Customer inquired about refund for defective product ordered on Jan 15th; support verified order details and shipping damage claim.
Refund of $129.99 approved and will be processed within 3-5 business days; customer satisfied with resolution.
============================================================
```

## Features

- **Speaker Diarization**: Identifies different speakers in the call
- **Smart Formatting**: Automatic punctuation and formatting
- **Batch Processing**: Handle multiple files at once
- **JSON Export**: All results saved for further processing
- **Clean Summaries**: Consistent two-line format for easy reading

## Troubleshooting

**Error: DEEPGRAM_API_KEY environment variable not set**
- Make sure you've exported your API keys (see Installation step 2)

**Error transcribing audio**
- Verify your Deepgram API key is valid
- Ensure the audio file is a valid M4A format
- Check your internet connection

**Error summarizing transcript**
- Verify your OpenRouter API key is valid
- Check that you have sufficient credits on OpenRouter
- Ensure the transcript isn't empty

## API Costs

- **Deepgram**: ~$0.0125 per minute of audio
- **OpenRouter (GPT-4)**: ~$0.03 per 1K input tokens, ~$0.06 per 1K output tokens

A typical 5-minute call costs approximately:
- Transcription: $0.06
- Summarization: $0.05
- **Total: ~$0.11 per call**

## License

MIT License - feel free to modify and use as needed.

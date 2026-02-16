#!/usr/bin/env python3
"""
Call Log Transcription and Summarization Script (Direct API Version)

This script:
1. Ingests M4A audio files
2. Transcribes them using Deepgram REST API (no SDK required)
3. Summarizes transcriptions using OpenRouter's OpenAI LLM API
4. Outputs clean, two-line summaries
"""

import os
import sys
from pathlib import Path
import requests
import json

# ============================================================================
# API KEYS CONFIGURATION
# ============================================================================
# IMPORTANT: Never commit your actual API keys to GitHub!
# Option 1: Hardcode your keys here for local testing (but DON'T commit them)
DEEPGRAM_API_KEY = ""  # Put your Deepgram API key here
OPENROUTER_API_KEY = ""  # Put your OpenRouter API key here

# Option 2: Use environment variables (more secure)
# If keys are not hardcoded above, they'll be read from environment variables
if not DEEPGRAM_API_KEY:
    DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
if not OPENROUTER_API_KEY:
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Validate API keys
if not DEEPGRAM_API_KEY:
    print("Error: DEEPGRAM_API_KEY not set")
    print("Either:")
    print("  1. Add your key to the script: DEEPGRAM_API_KEY = 'your_key_here'")
    print("  2. Set environment variable: $env:DEEPGRAM_API_KEY = 'your_key_here'")
    sys.exit(1)

if not OPENROUTER_API_KEY:
    print("Error: OPENROUTER_API_KEY not set")
    print("Either:")
    print("  1. Add your key to the script: OPENROUTER_API_KEY = 'your_key_here'")
    print("  2. Set environment variable: $env:OPENROUTER_API_KEY = 'your_key_here'")
    sys.exit(1)


def transcribe_audio(audio_file_path):
    """
    Transcribe an M4A audio file using Deepgram REST API directly
    
    Args:
        audio_file_path: Path to the M4A audio file
        
    Returns:
        str: Transcribed text
    """
    try:
        # Read audio file
        with open(audio_file_path, "rb") as audio:
            audio_data = audio.read()
        
        # Deepgram API endpoint
        url = "https://api.deepgram.com/v1/listen"
        
        # Query parameters for transcription options
        params = {
            "model": "nova-2",
            "smart_format": "true",
            "punctuate": "true",
            "diarize": "true",  # Speaker diarization for call logs
            "language": "en-US"
        }
        
        # Headers
        headers = {
            "Authorization": f"Token {DEEPGRAM_API_KEY}",
            "Content-Type": "audio/m4a"
        }
        
        # Make API request
        print(f"Sending {len(audio_data)} bytes to Deepgram...")
        response = requests.post(url, headers=headers, params=params, data=audio_data)
        response.raise_for_status()
        
        # Parse response
        result = response.json()
        transcript = result["results"]["channels"][0]["alternatives"][0]["transcript"]
        
        return transcript
        
    except requests.exceptions.RequestException as e:
        print(f"Error transcribing audio (HTTP): {e}")
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}")
        return None
    except Exception as e:
        print(f"Error transcribing audio: {e}")
        import traceback
        traceback.print_exc()
        return None


def summarize_transcript(transcript):
    """
    Summarize transcript using OpenRouter's OpenAI LLM API
    
    Args:
        transcript: The transcribed text
        
    Returns:
        str: Two-line summary
    """
    try:
        # System prompt for clean summarization
        system_prompt = """You are a professional call summarization assistant. 
Summarize call transcripts into exactly TWO concise lines:
Line 1: Main topic and key points discussed
Line 2: Action items, outcomes, or next steps

Be clear, professional, and concise."""

        # API request to OpenRouter
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "openai/gpt-4",  # Using OpenAI model via OpenRouter
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Summarize this call transcript:\n\n{transcript}"}
            ],
            "temperature": 0.3,
            "max_tokens": 150
        }
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload
        )
        
        response.raise_for_status()
        result = response.json()
        
        summary = result["choices"][0]["message"]["content"].strip()
        return summary
        
    except Exception as e:
        print(f"Error summarizing transcript: {e}")
        if hasattr(e, 'response') and hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}")
        return None


def process_call_log(audio_file_path):
    """
    Complete pipeline: transcribe and summarize a call log
    
    Args:
        audio_file_path: Path to the M4A audio file
    """
    print(f"\n{'='*60}")
    print(f"Processing: {Path(audio_file_path).name}")
    print(f"{'='*60}\n")
    
    # Step 1: Transcribe
    print("Step 1: Transcribing audio with Deepgram...")
    transcript = transcribe_audio(audio_file_path)
    
    if not transcript:
        print("❌ Transcription failed")
        return
    
    print(f"✓ Transcription complete ({len(transcript)} characters)")
    print(f"\nTranscript preview:\n{transcript[:200]}...\n")
    
    # Step 2: Summarize
    print("Step 2: Summarizing with OpenRouter OpenAI LLM...")
    summary = summarize_transcript(transcript)
    
    if not summary:
        print("❌ Summarization failed")
        return
    
    print(f"✓ Summary complete\n")
    print(f"{'='*60}")
    print("SUMMARY:")
    print(f"{'='*60}")
    print(summary)
    print(f"{'='*60}\n")
    
    return {
        "file": audio_file_path,
        "transcript": transcript,
        "summary": summary
    }


def main():
    """Main function to process call logs"""
    if len(sys.argv) < 2:
        print("Usage: python call_transcriber_direct.py <audio_file.m4a> [audio_file2.m4a ...]")
        print("\nMake sure to set API keys in the script or as environment variables")
        sys.exit(1)
    
    # Process each audio file
    results = []
    for audio_file in sys.argv[1:]:
        if not Path(audio_file).exists():
            print(f"⚠️  File not found: {audio_file}")
            continue
        
        if not audio_file.lower().endswith('.m4a'):
            print(f"⚠️  Not an M4A file: {audio_file}")
            continue
        
        result = process_call_log(audio_file)
        if result:
            results.append(result)
    
    # Save results to JSON
    if results:
        output_file = "call_summaries.json"
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\n✓ All results saved to {output_file}")


if __name__ == "__main__":
    main()

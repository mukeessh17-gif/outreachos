# week1/llm.py
# The ONLY file in OutreachOS that talks to an AI provider.
# If you switch from Gemini to another provider later, change only this file.
# Free tiers only - never use a paid API key here.

import os
import time
from dotenv import load_dotenv

# Load secrets from .env (GEMINI_API_KEY=your-key-here).
# .env is already in .gitignore - never commit it.
load_dotenv()

# TODO: Check Google AI Studio for the current free-tier model name.
# Do not guess. Common free-tier models include "gemini-1.5-flash" and
# "gemini-2.0-flash" but you should verify in the docs before using.
MODEL = "gemini-1.5-flash"


def ask_llm(prompt):
    """
    Sends a prompt to the AI provider and returns (text, input_tokens, output_tokens).
    On HTTP 429 (rate limit), waits and retries up to 3 times with increasing delays.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in .env file.")
        return None, 0, 0

    from google import genai
    client = genai.Client(api_key=api_key)

    delay = 2  # start with 2 seconds, then double each retry
    for attempt in range(3):
        try:
            response = client.models.generate_content(model=MODEL, contents=prompt)

            text = response.text

            # Try to read token usage from the response. Attribute names may vary
            # by SDK version - check the google-genai docs if these are 0.
            input_tokens = 0
            output_tokens = 0
            if hasattr(response, "usage_metadata"):
                input_tokens = getattr(response.usage_metadata, "prompt_token_count", 0)
                output_tokens = getattr(response.usage_metadata, "candidates_token_count", 0)

            return text, input_tokens, output_tokens

        except Exception as error:
            error_text = str(error)

            # HTTP 429 means rate limit - wait and retry with a longer delay.
            if "429" in error_text and attempt < 2:
                print(f"Rate limited. Waiting {delay}s before retry {attempt + 2}/3...")
                time.sleep(delay)
                delay *= 2  # 2s, then 4s
                continue

            print(f"Sorry, the AI call failed: {error}")
            return None, 0, 0

    print("Sorry, the AI call failed after 3 retries.")
    return None, 0, 0


# OPTIONAL: Offline version using Ollama (runs models on your own computer).
# Uncomment and adapt if you install Ollama and want to avoid the cloud API.
#
# def ask_llm_ollama(prompt):
#     import requests
#     response = requests.post(
#         "http://localhost:11434/api/generate",
#         json={"model": "llama3.2", "prompt": prompt, "stream": False},
#     )
#     return response.json()["response"], 0, 0
print("llm.py loaded. MODEL =", MODEL)
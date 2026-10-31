# Day 5: Call a free LLM API (Gemini)
# OutreachOS - AI sales outreach tool
# Run this file from inside the week1/ folder.

# ==================================================================
# 1. What is an API key? (5 lines)
# ==================================================================
# An API key is a secret password that identifies your program to an AI service.
# It lets the service know who is making the request and how to bill them.
# It must never be committed to Git because anyone who sees it can use your
# account, spend your money, or impersonate you.
# If a key leaks, revoke it immediately and generate a new one.
# Never paste real customer data when using a free-tier key.

# ==================================================================
# 2. .env setup (do this before running)
# ==================================================================
# Create a file named .env in the project root (outreachos/ folder):
#   GEMINI_API_KEY=your-actual-key-here
# Get your free key from Google AI Studio (no billing account required).
# .env is already in .gitignore. Verify with: git status
# Install dependencies:
#   pip install google-genai python-dotenv
#   (already added to requirements.txt)

# ==================================================================
# 3. Import ask_llm from llm.py (the only AI-provider file)
# ==================================================================
import os
import sys

# Make sure Python can find llm.py in the same folder.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from llm import ask_llm


# ==================================================================
# 4. Demo: call ask_llm and print token usage
# ==================================================================
print("Day 5 demo call:")
text, input_tokens, output_tokens = ask_llm("Say hello in one short sentence.")

if text:
    print("Response:", text)
    print("Input tokens:", input_tokens)
    print("Output tokens:", output_tokens)
else:
    print("No response received. Check your .env file and API key.")


# ==================================================================
# 5. TODO: summarize_company(name)
# ==================================================================
# TODO: Write summarize_company(name) here.
# It should:
#   - build a prompt asking for a 3-sentence summary of what the company does
#   - add a note that the answer is based on the model's general knowledge and may be wrong
#   - call ask_llm(prompt) and print the result plus token usage
# def summarize_company(name):
#     ...

print("Day 5 exercises complete.")
# Week 1 Checkpoint: CLI Tool
# OutreachOS - AI sales outreach tool
# Run this file from inside the week1/ folder.

import os
import sys

# Make sure Python can find llm.py and day3.py in the same folder.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from llm import ask_llm
from day3 import load_leads, save_leads

LEADS_FILE = "leads.json"


# ==================================================================
# TODO: Write summarize_company(name) here.
# It should:
#   - build a prompt asking for a 3-sentence summary of what the company does
#   - add a note that the answer is based on the model's general knowledge and may be wrong
#   - call ask_llm(prompt) to get (text, input_tokens, output_tokens)
#   - return a dictionary with keys: name, summary, input_tokens, output_tokens
#   - if the API call fails, return None
#
# def summarize_company(name):
#     prompt = f"..."
#     text, input_tokens, output_tokens = ask_llm(prompt)
#     if text is None:
#         return None
#     return {
#         "name": name,
#         "summary": text,
#         "input_tokens": input_tokens,
#         "output_tokens": output_tokens,
#     }
# ==================================================================


# ==================================================================
# TODO: Write the main loop here.
# It should:
#   - load existing leads with load_leads(LEADS_FILE)
#   - loop:
#       - ask the user: "Enter a company name:"
#       - if the user types "quit", break out of the loop
#       - if the input is empty (just Enter), print a friendly message and continue
#       - call summarize_company(name)
#       - if summarize_company returns None (API failed), print a friendly message and continue
#       - add the result dictionary to the leads list
#       - save the leads list with save_leads(LEADS_FILE, leads)
#   - when the loop ends, print a goodbye message
#
# Example of what the loop might look like (fill in the details yourself):
#
# leads = load_leads(LEADS_FILE)
#
# while True:
#     name = input("Enter a company name: ")
#     ...
# ==================================================================

print("OutreachOS CLI ready. TODO: write summarize_company() and the main loop above.")
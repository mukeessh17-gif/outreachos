# OutreachOS

AI-powered B2B sales outreach tool. Week 1 builds the core pieces: lists/dictionaries, JSON storage, HTTP APIs, and a free LLM for company summaries.

## What it does

- Stores lead information in dictionaries and lists (Day 2)
- Saves and loads leads from a JSON file (Day 3)
- Calls public HTTP APIs with error handling (Day 4)
- Calls a free LLM API (Gemini) for company summaries via `week1/llm.py` (Day 5)
- CLI tool that ties it all together: enter a company, get a summary, save it (Checkpoint)

## How to install

1. Open PowerShell in the `outreachos` folder.
2. Create a virtual environment:
   ```
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Create a `.env` file in the `outreachos` folder (not inside `week1`) with one line:
   ```
   GEMINI_API_KEY=your-key-here
   ```
   Get a free key from [Google AI Studio](https://aistudio.google.com/) — do not link a billing account.
   Never share your key. `.env` is in `.gitignore` and will not be committed.
5. Verify the model name in `week1/llm.py` matches a current free-tier model in Google AI Studio.

## How to run

From inside the `week1` folder:

- Run a single day:
  ```
  python day2.py
  python day3.py
  python day4.py
  python day5.py
  ```
- Run the checkpoint CLI tool:
  ```
  python outreach_cli.py
  ```
  (You will need to write the main loop and `summarize_company()` first — they are left as TODO skeletons.)

## Example output

```
Enter a company name: Kovai Textiles
Summary: Kovai Textiles is a textile manufacturer based in Coimbatore...
Note: This summary is based on the model's general knowledge and may be wrong.
Input tokens: 12
Output tokens: 48
Saved 1 leads to leads.json
Enter a company name: quit
Goodbye!
```

## Safety

- `.env` contains your API key and is listed in `.gitignore`. Never commit it.
- `.venv/` is also in `.gitignore`. It can be rebuilt from `requirements.txt`.
- Never paste real customer data into a free-tier LLM key.
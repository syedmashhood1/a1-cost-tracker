# Two-Provider Cost Tracker

Assignment 1 for the Agentic AI Developer course (IEC). The script sends the same prompt to **Google Gemini** and **Groq**, reads token counts from each API’s usage data, estimates cost from published per-million prices, prints a side-by-side table, and writes `results.json`.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)
- A Groq API key from the [GroqCloud console](https://console.groq.com/keys)

## Setup

```bash
git clone https://github.com/syedmashhood1/a1-cost-tracker.git
cd a1-cost-tracker
uv sync
cp .env.example .env
```

Edit `.env` and replace the placeholder values with your real keys. Model names and USD prices per 1M tokens also live in `.env`, so you can change them without editing the code.

## How to run

```bash
uv run tracker.py "Explain recursion in two short paragraphs."
```

The script prints each model’s reply, then a comparison table (provider, input tokens, output tokens, seconds, cost in USD), and saves `results.json` in the project root.

## Sample output

```
=== GEMINI (gemini-2.5-flash) ===
Recursion is a technique where a function solves a problem by calling
itself on a smaller instance of the same problem...

=== GROQ (openai/gpt-oss-20b) ===
Recursion means a function invokes itself until it reaches a base case...

=== COST COMPARISON ===
provider | input_tokens | output_tokens | seconds | cost_usd
---------+--------------+---------------+---------+-----------
gemini   | 12           | 148           | 1.842   | 0.00037360
groq     | 15           | 132           | 0.417   | 0.00004073

Saved results.json
```

Exact numbers will vary by prompt, model version, and network conditions. Token counts come from the APIs; they are not estimated by counting words.

## What I learned

Calling two providers from one script made it clear that “the same prompt” still produces different token counts, because each model tokenizes text differently. Reading usage from the response—and dividing by 1,000,000 for per-million prices—is the only reliable way to compare cost. Keeping keys in `.env` (and committing `.gitignore` before any secrets) is also non-negotiable if you want a clean Git history for grading.

## Notes

- Prices in `.env.example` follow the public paid-tier list rates for `gemini-2.5-flash` and `openai/gpt-oss-20b` (the Groq model available on this account’s free tier). Free-tier calls may not bill you, but the arithmetic still uses those rates for the assignment.
- If a key is missing or still a placeholder, the script exits with a clear message instead of crashing mid-request.

"""
Two-provider cost tracker.

Sends the same prompt to Google Gemini and Groq, reads token usage from each
API response, computes USD cost from per-million prices, prints a comparison
table, and writes results.json.
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any

from dotenv import load_dotenv
from google import genai
from groq import Groq


REQUIRED_KEYS = ("GEMINI_API_KEY", "GROQ_API_KEY")


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value or value.startswith("your_"):
        print(
            f"Missing or placeholder value for {name}. "
            f"Copy .env.example to .env and set a real key.",
            file=sys.stderr,
        )
        sys.exit(1)
    return value


def env_float(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        print(f"Invalid float for {name}: {raw!r}", file=sys.stderr)
        sys.exit(1)


def compute_cost(
    input_tokens: int,
    output_tokens: int,
    input_price_per_m: float,
    output_price_per_m: float,
) -> float:
    """USD cost = tokens × (price per 1M) / 1,000,000 for input and output."""
    return (
        input_tokens * input_price_per_m / 1_000_000
        + output_tokens * output_price_per_m / 1_000_000
    )


def call_gemini(prompt: str) -> dict[str, Any]:
    api_key = require_env("GEMINI_API_KEY")
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
    input_price = env_float("GEMINI_INPUT_PRICE_PER_M", 0.30)
    output_price = env_float("GEMINI_OUTPUT_PRICE_PER_M", 2.50)

    client = genai.Client(api_key=api_key)
    started = time.perf_counter()
    response = client.models.generate_content(model=model, contents=prompt)
    elapsed = time.perf_counter() - started

    usage = response.usage_metadata
    if usage is None:
        print("Gemini response did not include usage metadata.", file=sys.stderr)
        sys.exit(1)

    input_tokens = int(usage.prompt_token_count or 0)
    output_tokens = int(usage.candidates_token_count or 0)
    reply = (response.text or "").strip()
    cost = compute_cost(input_tokens, output_tokens, input_price, output_price)

    return {
        "provider": "gemini",
        "model": model,
        "reply": reply,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "input_price_per_m": input_price,
        "output_price_per_m": output_price,
        "cost_usd": cost,
        "seconds": round(elapsed, 3),
    }


def call_groq(prompt: str) -> dict[str, Any]:
    api_key = require_env("GROQ_API_KEY")
    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b").strip()
    input_price = env_float("GROQ_INPUT_PRICE_PER_M", 0.075)
    output_price = env_float("GROQ_OUTPUT_PRICE_PER_M", 0.30)

    client = Groq(api_key=api_key)
    started = time.perf_counter()
    completion = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    elapsed = time.perf_counter() - started

    usage = completion.usage
    if usage is None:
        print("Groq response did not include usage data.", file=sys.stderr)
        sys.exit(1)

    input_tokens = int(usage.prompt_tokens)
    output_tokens = int(usage.completion_tokens)
    reply = (completion.choices[0].message.content or "").strip()
    cost = compute_cost(input_tokens, output_tokens, input_price, output_price)

    return {
        "provider": "groq",
        "model": model,
        "reply": reply,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "input_price_per_m": input_price,
        "output_price_per_m": output_price,
        "cost_usd": cost,
        "seconds": round(elapsed, 3),
    }


def print_replies(results: list[dict[str, Any]]) -> None:
    for row in results:
        print(f"\n=== {row['provider'].upper()} ({row['model']}) ===")
        print(row["reply"])


def print_table(results: list[dict[str, Any]]) -> None:
    headers = ("provider", "input_tokens", "output_tokens", "seconds", "cost_usd")
    rows = [
        (
            r["provider"],
            str(r["input_tokens"]),
            str(r["output_tokens"]),
            f"{r['seconds']:.3f}",
            f"{r['cost_usd']:.8f}",
        )
        for r in results
    ]

    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def fmt(cols: tuple[str, ...] | list[str]) -> str:
        return " | ".join(cell.ljust(widths[i]) for i, cell in enumerate(cols))

    print("\n=== COST COMPARISON ===")
    print(fmt(headers))
    print("-+-".join("-" * w for w in widths))
    for row in rows:
        print(fmt(row))


def save_results(results: list[dict[str, Any]], path: str = "results.json") -> None:
    # Persist only the assignment fields (seconds is for the printed table).
    payload = [
        {
            "provider": r["provider"],
            "model": r["model"],
            "reply": r["reply"],
            "input_tokens": r["input_tokens"],
            "output_tokens": r["output_tokens"],
            "input_price_per_m": r["input_price_per_m"],
            "output_price_per_m": r["output_price_per_m"],
            "cost_usd": r["cost_usd"],
        }
        for r in results
    ]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"\nSaved {path}")


def main() -> None:
    # Windows terminals often default to cp1252; model replies may include Unicode.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    load_dotenv()

    if len(sys.argv) < 2 or not sys.argv[1].strip():
        print('Usage: uv run tracker.py "your prompt"', file=sys.stderr)
        sys.exit(1)

    prompt = sys.argv[1].strip()

    # Fail early with a clear message if either key is missing.
    for key in REQUIRED_KEYS:
        require_env(key)

    results = [call_gemini(prompt), call_groq(prompt)]
    print_replies(results)
    print_table(results)
    save_results(results)


if __name__ == "__main__":
    main()

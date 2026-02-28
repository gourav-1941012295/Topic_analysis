"""Shared LLM helpers: one place for OpenAI client and simple completion."""

import json
import os


def get_client():
    """Return OpenAI client or None if key missing."""
    try:
        from openai import OpenAI
        key = os.environ.get("OPENAI_API_KEY")
        return OpenAI(api_key=key) if key else None
    except Exception:
        return None


def complete(prompt: str, temperature: float = 0.2, model: str | None = None) -> str | None:
    """One LLM call. Returns content string or None on failure."""
    client = get_client()
    if not client:
        return None
    model = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    try:
        r = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        return (r.choices[0].message.content or "").strip()
    except Exception:
        return None


def complete_json(prompt: str, temperature: float = 0.2) -> dict | None:
    """Like complete() but strips markdown and parses JSON. Returns dict or None."""
    content = complete(prompt, temperature=temperature)
    if not content:
        return None
    if "```" in content:
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return None

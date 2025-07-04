"""Earnings-call transcript summariser.

Given a raw transcript (string), returns:
  • key_bullets – 5-7 concise take-away bullets  
  • risks – 3-4 bullet risk / concern highlights

Implementation uses LangChain with the OpenAI ChatCompletion endpoint.  If the
`OPENAI_API_KEY` env variable is absent the module falls back to a simple
sentence-extraction heuristic so the rest of the pipeline continues to work in
open-source environments.
"""
from __future__ import annotations

import os
from typing import Dict, List

try:
    from langchain_openai import ChatOpenAI  # type: ignore
    from langchain.chains import LLMChain  # type: ignore
    from langchain.prompts import PromptTemplate  # type: ignore
except ImportError:  # pragma: no cover
    ChatOpenAI = None  # type: ignore

# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------

PROMPT_TMPL = """You are an expert equity analyst.
Summarise the following earnings-call transcript.  Provide two sections:
1. Key Take-Aways – 5 to 7 concise bullets.
2. Risks / Concerns – 3 to 4 concise bullets focusing on negatives.
Return the answer as JSON with keys: key_bullets (list), risks (list).

Transcript:
```\n{transcript}\n```
"""

prompt = PromptTemplate.from_template(PROMPT_TMPL)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def summarise_transcript(transcript: str) -> Dict[str, List[str]]:  # noqa: D401
    """Return bullet summary & risks list for an earnings transcript."""

    if ChatOpenAI is None or os.getenv("OPENAI_API_KEY") is None:
        return _fallback_summary(transcript)

    llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0.3)
    chain = LLMChain(prompt=prompt, llm=llm)
    res = chain.invoke({"transcript": transcript})

    try:
        import json

        parsed = json.loads(res["text"] if isinstance(res, dict) else res)
        # ensure lists
        return {
            "key_bullets": parsed.get("key_bullets", []),
            "risks": parsed.get("risks", []),
        }
    except Exception:
        # fallback to heuristic if parsing fails
        return _fallback_summary(transcript)


# ---------------------------------------------------------------------------
# Fallback heuristic
# ---------------------------------------------------------------------------

def _fallback_summary(text: str) -> Dict[str, List[str]]:  # noqa: D401
    """Naive fallback: pick first/last sentences and look for risk words."""

    import re

    sentences = re.split(r"(?<=[.!?])\s+", text)
    key_bullets = sentences[:3]  # first 3 sentences as proxy

    risk_keywords = ["risk", "concern", "challenge", "headwind", "pressure"]
    risks: List[str] = []
    for s in sentences:
        if any(k in s.lower() for k in risk_keywords):
            risks.append(s)
        if len(risks) >= 3:
            break

    return {"key_bullets": key_bullets, "risks": risks}
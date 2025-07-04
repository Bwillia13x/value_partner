"""Competitive-advantage (economic moat) detection pipeline.

For each input text (e.g. MD&A section, earnings call transcript) the
`analyze_text` function returns a confidence score 0-1 for the following moat
archetypes:

• Network Effects
• Low-Cost Producer
• Switching Costs
• Intangibles / Brand / IP
• Regulatory / Government Barriers

The current algorithm is lightweight yet extensible:
1. Keyword seed lists per moat category.
2. Encode both keywords and text sentences via a pre-trained
   *all-MiniLM-L6-v2* sentence-transformer.
3. Compute cosine similarity; final score = max similarity among matches,
   scaled to [0, 1].

Later iterations can swap to finetuned models (FinBERT, domain-specific
Sentence-T5), add pattern rules or incorporate 10-K section weighting.
"""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Dict, List

import numpy as np
from sentence_transformers import SentenceTransformer, util  # type: ignore

from services.db.database import SessionLocal
from services.db.models import QualitativeSignal  # type: ignore[attr-defined]

# ---------------------------------------------------------------------------
# Model & embeddings
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _model() -> SentenceTransformer:  # noqa: D401
    """Singleton sentence-transformer model."""
    return SentenceTransformer("all-MiniLM-L6-v2")


MOAT_KEYWORDS: Dict[str, List[str]] = {
    "network_effects": [
        "network effects",
        "two-sided marketplace",
        "platform lock-in",
        "user base scale",
        "virality",
    ],
    "low_cost_producer": [
        "cost leadership",
        "lowest unit cost",
        "economies of scale",
        "cost advantage",
    ],
    "switching_costs": [
        "switching costs",
        "customer retention",
        "high stickiness",
        "long-term contracts",
    ],
    "intangibles": [
        "brand strength",
        "intellectual property",
        "patent portfolio",
        "proprietary technology",
    ],
    "regulatory": [
        "license monopoly",
        "regulatory approval",
        "government granted",
        "compliance barrier",
    ],
}


def _clean_sentences(text: str) -> List[str]:
    """Split *text* into simple sentences for embedding."""
    # naive sentence split; could replace with nltk or spacy later
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def analyze_text(text: str) -> Dict[str, float]:
    """Return moat confidence dict for a given piece of text.

    Values are in [0, 1]. A basic threshold like >0.4 can flag presence.
    """
    model = _model()
    sentences = _clean_sentences(text.lower())
    if not sentences:
        return {tag: 0.0 for tag in MOAT_KEYWORDS}

    sent_emb = model.encode(sentences, convert_to_tensor=True, normalize_embeddings=True)

    scores: Dict[str, float] = {}
    for tag, seeds in MOAT_KEYWORDS.items():
        seed_emb = model.encode(seeds, convert_to_tensor=True, normalize_embeddings=True)
        # cosine similarities: shape (len(seeds), len(sentences)) – take max
        cos = util.cos_sim(seed_emb, sent_emb).cpu().numpy()  # type: ignore[arg-type]
        max_sim = float(np.max(cos)) if cos.size else 0.0
        # scale similarity (-1..1) to 0..1 for ease-of-use
        scores[tag] = max(0.0, max_sim)
    return scores


def store_signal(symbol: str, source: str, text: str) -> None:
    """Analyze *text* and persist qualitative signals rows (one per moat)."""
    scores = analyze_text(text)
    session = SessionLocal()
    try:
        for tag, score in scores.items():
            signal = QualitativeSignal(
                symbol=symbol.upper(),
                moat_tag=tag,
                score=score,
                source=source,
            )
            session.add(signal)
        session.commit()
    finally:
        session.close()
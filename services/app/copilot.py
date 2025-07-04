"""copilot.py

NLP Copilot: simple retrieval-augmented answer generation based on internal markdown/docs.
Uses SentenceTransformer embeddings + cosine similarity.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List

import numpy as np
from sentence_transformers import SentenceTransformer

DOC_DIRS = [Path("docs"), Path("README.md")]
MODEL_NAME = "all-MiniLM-L6-v2"


class CopilotRetriever:
    def __init__(self):
        self.model = SentenceTransformer(MODEL_NAME)
        self.corpus_chunks: List[str] = []
        self.embeddings: np.ndarray | None = None
        self._load_corpus()

    def _load_corpus(self):
        texts = []
        for d in DOC_DIRS:
            if d.is_file():
                texts.append(d.read_text())
            elif d.is_dir():
                for p in d.rglob("*.md"):
                    texts.append(p.read_text())
        # chunk by paragraphs
        chunks = []
        for t in texts:
            for para in re.split(r"\n{2,}", t):
                if len(para.strip()) > 50:
                    chunks.append(para.strip())
        self.corpus_chunks = chunks
        self.embeddings = self.model.encode(chunks, convert_to_numpy=True, show_progress_bar=False)

    def query(self, q: str, k: int = 3) -> List[str]:
        q_emb = self.model.encode(q, convert_to_numpy=True)
        sims = np.dot(self.embeddings, q_emb) / (
            np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(q_emb) + 1e-9
        )
        top_idx = sims.argsort()[-k:][::-1]
        return [self.corpus_chunks[i] for i in top_idx]
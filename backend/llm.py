import os
import sys
import logging
import re
from typing import List

# Append parent directory to sys.path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sentence_transformers import SentenceTransformer, util

logger = logging.getLogger(__name__)

# Lazy-loaded sentence transformer model
_st_model = None


def _get_st_model():
    global _st_model
    if _st_model is None:
        # lightweight, widely available model
        _st_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _st_model


def _split_sentences(text: str) -> List[str]:
    # Simple sentence splitter; avoids heavy deps
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    # Filter out very short fragments
    return [p.strip() for p in parts if len(p.strip()) > 20]


def _extract_summary(text_corpus: str, max_sentences: int = 5) -> str:
    """
    Use sentence embeddings to select representative sentences from the corpus.
    """
    sentences = _split_sentences(text_corpus)
    if not sentences:
        return "Summary unavailable."

    model = _get_st_model()
    # Compute embeddings for sentences and centroid
    sent_embs = model.encode(sentences, convert_to_tensor=True)
    centroid = sent_embs.mean(dim=0, keepdim=True)
    sims = util.cos_sim(sent_embs, centroid).cpu().numpy().reshape(-1)

    # Rank sentences by similarity to centroid
    ranked = sorted(zip(sims, sentences), key=lambda x: x[0], reverse=True)
    top_sentences = [s for _, s in ranked[:max_sentences]]
    return " ".join(top_sentences)


def generate_gemini_summary(text_corpus: str) -> dict:
    """
    Groq/Gemini disabled: build a summary from the corpus using sentence-transformer scoring.
    """
    try:
        summary = _extract_summary(text_corpus, max_sentences=5)
    except Exception as e:
        logger.warning(f"Sentence-transformer summary failed, using fallback: {e}")
        words = text_corpus.split()
        summary = " ".join(words[:120]) if words else "Summary unavailable."

    return {
        "role": None,
        "summary": summary,
    }


def rank_recommendations_with_gemini(candidates: list, profile_context: str) -> list:
    """
    Groq/Gemini disabled: return the locally ranked candidates unchanged.
    """
    return candidates[:5] if candidates else []


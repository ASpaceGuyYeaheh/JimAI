import json
import re
from pathlib import Path
from typing import List, Dict, Any


class KnowledgeBase:
    """A tiny, local knowledge base for space facts.

    This keeps a small JSON file of space facts and provides a simple
    keyword-based lookup. It's intentionally simple so beginners can
    read and modify it easily.
    """

    def __init__(self, file_path: str = "space_facts.json"):
        self.file_path = Path(file_path)
        self.facts = self._load()

    def _load(self) -> List[Dict[str, Any]]:
        if not self.file_path.exists():
            return []
        try:
            with self.file_path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
                if isinstance(data, list):
                    return data
        except (json.JSONDecodeError, OSError):
            pass
        return []

    def _extract_keywords(self, text: str) -> List[str]:
        if not text:
            return []
        cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
        parts = [p for p in cleaned.split() if len(p) > 2]
        return parts

    def find_relevant(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Return up to `limit` facts that match the query keywords.

        Very simple scoring: count keyword occurrences in each fact's text.
        """
        if not query or not self.facts:
            return []

        keywords = self._extract_keywords(query)
        if not keywords:
            return []

        scores = []
        for i, fact in enumerate(self.facts):
            text = fact.get("text", "").lower()
            score = 0
            for kw in keywords:
                score += text.count(kw)
            if score > 0:
                scores.append((score, i, fact))

        scores.sort(key=lambda t: (-t[0], t[1]))
        return [t[2] for t in scores[:limit]]

    def get_all(self) -> List[Dict[str, Any]]:
        return self.facts

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import re

STOPWORDS = {
    "the", "is", "at", "which", "on", "a", "an", "and", "or", "in", "of",
    "to", "for", "with", "that", "this", "it", "as", "are", "was", "were",
}


class Memory:
    """A very simple memory system for a beginner AI project.

    This stores memories as a list of entries in a JSON file.
    Each entry contains:
    - text: the memory content
    - created_at: a timestamp
    """

    def __init__(self, file_path: str = "memory.json"):
        self.file_path = Path(file_path)
        self.memories = self._load()

    def _load(self) -> List[Dict[str, Any]]:
        if not self.file_path.exists():
            return []

        try:
            with self.file_path.open("r", encoding="utf-8") as file:
                data = json.load(file)
                if isinstance(data, list):
                    return data
        except (json.JSONDecodeError, OSError):
            pass

        return []

    def _save(self) -> None:
        with self.file_path.open("w", encoding="utf-8") as file:
            json.dump(self.memories, file, indent=2, ensure_ascii=False)

    def add(self, text: str) -> Dict[str, Any]:
        if not text or not text.strip():
            return {}

        memory = {
            "text": text.strip(),
            "created_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        }
        self.memories.append(memory)
        self._save()
        return memory

    def get_recent(self, limit: int = 5) -> List[Dict[str, Any]]:
        return list(reversed(self.memories[-limit:]))

    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Simple substring search (keeps backward compatibility)."""
        if not query:
            return []

        lower_query = query.lower()
        matches = []

        for memory in self.memories:
            text = memory.get("text", "")
            if lower_query in text.lower():
                matches.append(memory)

        return matches[-limit:]

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract candidate keywords from some text.

        - Lowercases
        - Removes punctuation
        - Splits on whitespace
        - Filters out short words and stopwords
        """
        if not text:
            return []

        cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
        parts = [p for p in cleaned.split() if len(p) > 2 and p not in STOPWORDS]
        return parts

    def _clean_memory_text(self, text: str) -> str:
        """Remove wrapper prefixes like 'User said:' and trailing timestamp ' at YYYY-MM-DDTHH:MM:SS'.

        Returns a cleaned, human-friendly version of a saved memory text.
        """
        if not text:
            return ""

        cleaned = re.sub(r"^(User said:|Told user a fact:)\s*", "", text, flags=re.IGNORECASE)
        # remove trailing ' at 2026-10-17T16:43:11' style timestamp
        cleaned = re.sub(r"\s+at\s+\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$", "", cleaned)
        return cleaned.strip()

    def find_relevant(self, query: str, limit: int = 5, exclude_text: Optional[str] = None) -> List[Dict[str, Any]]:
        """Find memories that are most relevant to the query using simple keyword matching.

        Optionally exclude memories that match or contain `exclude_text` to avoid
        returning the user's current question as a memory match.
        """
        if not query or not self.memories:
            return []

        keywords = self._extract_keywords(query)
        if not keywords:
            return []

        exclude_norm = (exclude_text or "").lower().strip()
        # normalize exclude by removing surrounding punctuation
        exclude_norm = re.sub(r"[^a-zA-Z0-9\s]", " ", exclude_norm)

        scores = []  # tuples (score, index, memory)

        for i, memory in enumerate(self.memories):
            raw_text = memory.get("text", "")
            # skip exact/near-exact matches to the input so questions don't match themselves
            if exclude_norm and exclude_norm in re.sub(r"[^a-zA-Z0-9\s]", " ", raw_text.lower()):
                continue

            text = raw_text.lower()
            score = 0
            for kw in keywords:
                # count simple occurrences
                score += text.count(kw)

            if score > 0:
                scores.append((score, i, memory))

        # sort by score descending, then by index (oldest first among ties)
        scores.sort(key=lambda t: (-t[0], t[1]))

        # return only the memory objects, keep most recent matches first
        results = [t[2] for t in scores[:limit]]
        return results

    def get_all(self) -> List[Dict[str, Any]]:
        return self.memories

    def clear(self) -> None:
        self.memories = []
        self._save()

import json
from pathlib import Path
from typing import List, Dict, Any


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
        if not query:
            return []

        lower_query = query.lower()
        matches = []

        for memory in self.memories:
            text = memory.get("text", "")
            if lower_query in text.lower():
                matches.append(memory)

        return matches[-limit:]

    def get_all(self) -> List[Dict[str, Any]]:
        return self.memories

    def clear(self) -> None:
        self.memories = []
        self._save()

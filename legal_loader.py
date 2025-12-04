# legal_loader.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import yaml  # pip install pyyaml


@dataclass
class LegalSnippet:
    id: str
    title: str
    tags: List[str]
    profil: str
    jurisdiction: str
    sources: List[str]
    priority: int
    active: bool
    version: int
    date_added: str
    text: str
    path: str


class LegalRepository:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.snippets_by_id: Dict[str, LegalSnippet] = {}
        self.snippets_by_tag: Dict[str, List[LegalSnippet]] = {}

    def load(self) -> None:
        """legal_texts klasöründeki tüm .md dosyalarını okuyup hafızaya alır."""
        self.snippets_by_id.clear()
        self.snippets_by_tag.clear()

        for md_file in self.base_dir.rglob("*.md"):
            snippet = self._load_single_file(md_file)
            if snippet is None:
                continue
            if not snippet.active:
                continue
            # ID uniq olsun
            if snippet.id in self.snippets_by_id:
                # Çakışma varsa daha yüksek priority'li veya daha yeni olanı almayı seçebilirsin.
                # Şimdilik ilk görüleni koruyalım.
                continue

            self.snippets_by_id[snippet.id] = snippet
            for tag in snippet.tags:
                self.snippets_by_tag.setdefault(tag, []).append(snippet)

        # Tag altındaki snippet'leri priority'ye göre sırala
        for tag, lst in self.snippets_by_tag.items():
            lst.sort(key=lambda s: s.priority)

    def _load_single_file(self, path: Path) -> Optional[LegalSnippet]:
        text = path.read_text(encoding="utf-8")
        text = text.lstrip()
        if not text.startswith("---"):
            # YAML yoksa bu dosyayı şimdilik yok say
            return None

        # İlk iki '---' arasında YAML, sonrası metin
        parts = text.split("---", 2)
        if len(parts) < 3:
            return None

        _, yaml_part, body_part = parts
        meta = yaml.safe_load(yaml_part)

        # Zorunlu alanlar
        sid = meta.get("id")
        title = meta.get("title", "")
        tags = meta.get("tags", [])
        profil = meta.get("profil", "Ortak")
        jurisdiction = meta.get("jurisdiction", "TR")
        sources = meta.get("sources", [])
        priority = int(meta.get("priority", 100))
        active = bool(meta.get("active", True))
        version = int(meta.get("version", 1))
        date_added = str(meta.get("date_added", ""))

        body = body_part.strip()

        if not sid:
            return None

        return LegalSnippet(
            id=sid,
            title=title,
            tags=tags,
            profil=profil,
            jurisdiction=jurisdiction,
            sources=sources,
            priority=priority,
            active=active,
            version=version,
            date_added=date_added,
            text=body,
            path=str(path),
        )

    def find_by_tag(self, tag: str) -> List[LegalSnippet]:
        """Belirli bir tag'e sahip snippet'leri priority sırasına göre döndürür."""
        return list(self.snippets_by_tag.get(tag, []))

    def find_by_id(self, sid: str) -> Optional[LegalSnippet]:
        return self.snippets_by_id.get(sid)

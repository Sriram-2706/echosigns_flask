import os
import re
from typing import List, Tuple, Dict
from .local_nlp import tokenize, filter_keywords, hi_to_en_glossary, normalize_text

class Text2ISL:
    """
    Maps English (or glossary-mapped Hindi) tokens/phrases to ISL video files.
    Strategy:
      1) Build a set of available video names (without extension).
      2) Greedy phrase match on up to N tokens (prefers longest).
      3) Fallback: letters A–Z or digits 0–9 if video exists.
    Filenames can include spaces (e.g., 'Thank You.mp4'), so we keep phrase variants too.
    """
    def __init__(self, video_root: str, max_phrase_len: int = 3):
        self.video_root = video_root
        self.max_phrase_len = max_phrase_len
        self.inventory = self._scan_inventory()

    def _scan_inventory(self) -> Dict[str, str]:
        inv = {}
        if not os.path.isdir(self.video_root):
            return inv
        for fn in os.listdir(self.video_root):
            if not fn.lower().endswith(".mp4"):
                continue
            stem = fn[:-4]  # remove .mp4
            key_norm = normalize_text(stem)  # e.g., "thank you"
            inv[key_norm] = fn  # store original filename to preserve case/spaces
        return inv

    def _greedy_phrase_match(self, tokens: List[str]) -> Tuple[List[str], List[str]]:
        """
        Returns: (keywords, files)
        """
        i = 0
        keywords, files = [], []
        n = len(tokens)
        while i < n:
            matched = False
            # try longest first
            for L in range(min(self.max_phrase_len, n - i), 0, -1):
                phrase = " ".join(tokens[i:i+L])
                # direct phrase
                if phrase in self.inventory:
                    keywords.append(phrase)
                    files.append(self.inventory[phrase])
                    i += L
                    matched = True
                    break
                # Title-case single word fallback (e.g., "Hello" vs "hello")
                if L == 1:
                    title_phrase = phrase.capitalize()
                    if title_phrase.lower() in self.inventory:
                        keywords.append(phrase)
                        files.append(self.inventory[title_phrase.lower()])
                        i += 1
                        matched = True
                        break
            if not matched:
                # fallback to spell-out letters/digits if present in inventory
                tok = tokens[i]
                added_any = False
                # Alphanumeric fallback
                for ch in tok:
                    if ch.isalnum():
                        key = ch.upper() if ch.isalpha() else ch
                        if key.lower() in self.inventory:
                            keywords.append(key)
                            files.append(self.inventory[key.lower()])
                            added_any = True
                        elif key in self.inventory:
                            keywords.append(key)
                            files.append(self.inventory[key])
                if not added_any:
                    # if no fallback, skip token
                    pass
                i += 1
        return keywords, files

    def text_to_playlist(self, text: str, lang: str = "en") -> Tuple[List[str], List[str]]:
        # Hindi → English via simple glossary (placeholder for real translator)
        if lang.lower().startswith("hi"):
            text = hi_to_en_glossary(text)
        toks = tokenize(text)
        toks = filter_keywords(toks)
        if not toks:
            return [], []
        return self._greedy_phrase_match(toks)

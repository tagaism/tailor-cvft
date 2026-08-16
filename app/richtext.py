from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from typing import Any


class _RichParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.stack: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() in {"br", "div", "p"}:
            if tag.lower() == "br" or self.parts:
                self.parts.append("<br>")
            return
        mapped = _map_tag(tag)
        if mapped:
            self.parts.append(f"<{mapped}>")
            self.stack.append(mapped)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"div", "p"}:
            self.parts.append("<br>")
            return
        mapped = _map_tag(tag)
        if mapped and mapped in self.stack:
            while self.stack:
                last = self.stack.pop()
                self.parts.append(f"</{last}>")
                if last == mapped:
                    break

    def handle_data(self, data: str) -> None:
        self.parts.append(html.escape(data, quote=False))

    def close(self) -> str:
        super().close()
        while self.stack:
            self.parts.append(f"</{self.stack.pop()}>")
        text = "".join(self.parts)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"(?:<br>\s*){3,}", "<br><br>", text)
        text = re.sub(r"^(?:<br>)+|(?:<br>)+$", "", text).strip()
        return text


def _map_tag(tag: str) -> str:
    tag = tag.lower()
    if tag in {"b", "strong"}:
        return "b"
    if tag in {"i", "em"}:
        return "i"
    return ""


def sanitize_rich(value: str) -> str:
    text = "" if value is None else str(value)
    parser = _RichParser()
    try:
        parser.feed(text)
        return parser.close()
    except Exception:
        return html.escape(re.sub(r"<[^>]+>", "", text), quote=False)


def apply_cv_path(cv: dict[str, Any], path: str, value: str) -> None:
    if not re.fullmatch(r"[a-zA-Z0-9]+(?:\.[a-zA-Z0-9]+)*", path or ""):
        raise ValueError("Invalid path.")
    parts = path.split(".")
    node: Any = cv
    for part in parts[:-1]:
        key: Any = int(part) if part.isdigit() else part
        node = node[key]
    last = parts[-1]
    key = int(last) if last.isdigit() else last
    node[key] = value


def rich_tokens(value: str) -> list[tuple[str, str]]:
    """Yield ('text', s) or ('style', 'B'|'I'|'') tokens for PDF drawing."""
    clean = sanitize_rich(value)
    tokens: list[tuple[str, str]] = []
    bold = italic = False

    def style() -> str:
        if bold and italic:
            return "BI"
        if bold:
            return "B"
        if italic:
            return "I"
        return ""

    pos = 0
    for match in re.finditer(r"<br\s*/?>|</?(b|i)>", clean, flags=re.I):
        if match.start() > pos:
            tokens.append((style(), html.unescape(clean[pos : match.start()])))
        tag = match.group(0).lower()
        if tag.startswith("<br"):
            tokens.append(("br", "\n"))
        elif tag == "<b>":
            bold = True
        elif tag == "</b>":
            bold = False
        elif tag == "<i>":
            italic = True
        elif tag == "</i>":
            italic = False
        pos = match.end()
    if pos < len(clean):
        tokens.append((style(), html.unescape(clean[pos:])))
    return [(style, text) for style, text in tokens if text]

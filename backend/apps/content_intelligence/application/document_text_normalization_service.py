from __future__ import annotations

import re
import unicodedata
from collections import Counter

from apps.content_intelligence.domain.services import DocumentNormalizationResult


class DocumentTextNormalizationService:
    _CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")
    _DATE_LINE = re.compile(
        r"^(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+\d{1,2}(?:,\s*\d{4})?$",
        re.IGNORECASE,
    )
    _ROMAN_LINE = re.compile(r"^[ivxlcdm]{1,8}$", re.IGNORECASE)
    _PAGE_MARKER = re.compile(r"^(?:page\s+)?\d{1,4}$", re.IGNORECASE)
    _CONTENTS_LINE = re.compile(r".+\.{2,}\s*\d+$")
    _NAVIGATION_KEYWORDS = re.compile(r"\b(contents?|table of contents|index|bibliography|acknowledg(?:e)?ments?|dedication|preface|copyright|isbn|publisher)\b", re.IGNORECASE)
    _ISBN_LINE = re.compile(r"^isbn(?:-13|-10)?[:\s]+\S+", re.IGNORECASE)
    _COPYRIGHT_LINE = re.compile(r"^(?:copyright|all rights reserved|published by)\b", re.IGNORECASE)
    _BROKEN_OCR = re.compile(r"\b[a-zA-Z]+\d+[A-Z][a-zA-Z]*\b|\b\d+[A-Z][a-zA-Z]+\b")
    _DOT_LEADER = re.compile(r"\.{2,}")

    def normalize(self, text: str) -> DocumentNormalizationResult:
        normalized_text = self._normalize_text(text)
        lines = normalized_text.splitlines()
        repeated_headers = self._detect_repeated_headers(lines)

        cleaned_lines: list[str] = []
        diagnostics = {
            "lines_removed": 0,
            "repeated_headers_removed": 0,
            "page_markers_removed": 0,
            "date_lines_removed": 0,
            "front_matter_lines_classified": 0,
            "malformed_lines_flagged": 0,
            "table_of_contents_lines_removed": 0,
            "classified_line_counts": {},
        }

        for line in lines:
            classification = self.classify_line(line, repeated_headers=repeated_headers)
            classified_counts = diagnostics["classified_line_counts"]
            classified_counts[classification] = classified_counts.get(classification, 0) + 1

            if classification == "academic_content":
                cleaned_lines.append(line)
                continue

            diagnostics["lines_removed"] += 1
            if classification == "repeated_header_footer":
                diagnostics["repeated_headers_removed"] += 1
            elif classification == "page_marker":
                diagnostics["page_markers_removed"] += 1
            elif classification == "date_like":
                diagnostics["date_lines_removed"] += 1
            elif classification in {"front_matter", "navigation", "reference"}:
                diagnostics["front_matter_lines_classified"] += 1
            elif classification == "table_of_contents":
                diagnostics["table_of_contents_lines_removed"] += 1
            elif classification == "malformed_fragment":
                diagnostics["malformed_lines_flagged"] += 1

        cleaned_text = self._collapse_blank_lines("\n".join(cleaned_lines))
        return DocumentNormalizationResult(
            normalized_text=normalized_text,
            cleaned_text=cleaned_text,
            metadata=diagnostics,
        )

    def classify_line(self, line: str, *, repeated_headers: set[str] | None = None) -> str:
        candidate = line.strip()
        if not candidate:
            return "blank"
        lowered = candidate.lower()
        repeated_headers = repeated_headers or set()
        if candidate in repeated_headers:
            return "repeated_header_footer"
        if self._PAGE_MARKER.fullmatch(candidate) or self._ROMAN_LINE.fullmatch(candidate):
            return "page_marker"
        if self._DATE_LINE.fullmatch(candidate):
            return "date_like"
        if self._DOT_LEADER.search(candidate) and self._CONTENTS_LINE.match(candidate):
            return "table_of_contents"
        if self._ISBN_LINE.match(candidate) or self._COPYRIGHT_LINE.match(candidate):
            return "front_matter"
        if self._NAVIGATION_KEYWORDS.search(lowered):
            if "index" in lowered or "bibliography" in lowered:
                return "reference"
            if "contents" in lowered:
                return "navigation"
            return "front_matter"
        if self._BROKEN_OCR.search(candidate):
            return "malformed_fragment"
        if self._looks_like_short_navigation(candidate):
            return "navigation"
        return "academic_content"

    def _normalize_text(self, value: str) -> str:
        normalized = unicodedata.normalize("NFKC", value or "")
        normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
        normalized = self._CONTROL_CHARACTERS.sub("", normalized)
        normalized = "\n".join(re.sub(r"[ \t]+", " ", line).strip() for line in normalized.splitlines())
        return self._collapse_blank_lines(normalized)

    def _collapse_blank_lines(self, value: str) -> str:
        return re.sub(r"\n{3,}", "\n\n", value).strip()

    def _detect_repeated_headers(self, lines: list[str]) -> set[str]:
        candidates = [line.strip() for line in lines if 0 < len(line.strip()) <= 80]
        repeated = Counter(candidates)
        return {line for line, count in repeated.items() if count >= 2 and self._looks_like_header_footer(line)}

    def _looks_like_header_footer(self, line: str) -> bool:
        lowered = line.lower()
        if self._PAGE_MARKER.fullmatch(line) or self._ROMAN_LINE.fullmatch(line):
            return True
        if self._NAVIGATION_KEYWORDS.search(lowered):
            return True
        alpha_ratio = sum(char.isalpha() for char in line) / max(len(line), 1)
        return alpha_ratio >= 0.5 and len(line.split()) <= 6

    def _looks_like_short_navigation(self, line: str) -> bool:
        tokens = line.split()
        if len(tokens) > 6:
            return False
        if re.match(r"^(chapter|section|unit|lesson|topic)\b", line, re.IGNORECASE):
            return False
        if self._DOT_LEADER.search(line):
            return True
        numeric_tokens = sum(token.isdigit() for token in tokens)
        return bool(numeric_tokens and numeric_tokens >= max(1, len(tokens) - 1))

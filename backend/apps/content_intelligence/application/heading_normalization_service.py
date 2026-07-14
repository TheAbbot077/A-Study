from __future__ import annotations

import re

from apps.content_intelligence.domain.services import HeadingNormalizationResult


class HeadingNormalizationService:
    _SEQUENCE_WORDS = {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
        "eleven": 11,
        "twelve": 12,
        "first": 1,
        "second": 2,
        "third": 3,
        "fourth": 4,
        "fifth": 5,
        "sixth": 6,
        "seventh": 7,
        "eighth": 8,
        "ninth": 9,
        "tenth": 10,
        "eleventh": 11,
        "twelfth": 12,
    }
    _ROMAN_MAP = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7, "viii": 8, "ix": 9, "x": 10, "xi": 11, "xii": 12}
    _STRUCTURED_PATTERNS = [
        re.compile(
            r"^(?P<prefix>chapter|section|unit|lesson|topic)\s+(?P<sequence>\d+|[ivxlcdm]+|[A-Za-z]+)(?:\s*[:.\-]\s*|\s+)(?P<title>.+)$",
            re.IGNORECASE,
        ),
        re.compile(r"^(?P<sequence>\d+(?:\.\d+)*)\s*[:.\-)]\s*(?P<title>.+)$"),
    ]
    _GENERIC_PATTERNS = [
        re.compile(r"^(?P<prefix>chapter|section|unit|lesson|topic)\s+(?P<sequence>\d+|[ivxlcdm]+|[A-Za-z]+)$", re.IGNORECASE),
        re.compile(r"^(?P<sequence>\d+(?:\.\d+)*)$", re.IGNORECASE),
    ]
    _MALFORMED_TOKEN_PATTERN = re.compile(r"\d+[A-Z][a-zA-Z]+|[a-z][A-Z]{2,}")

    def normalize(self, heading: str) -> HeadingNormalizationResult:
        original = heading or ""
        normalized = self._normalize_text(original)
        malformed_tokenization = bool(self._MALFORMED_TOKEN_PATTERN.search(normalized.replace(" ", "")))
        metadata: dict[str, object] = {"token_count": len(normalized.split())}

        for pattern in self._STRUCTURED_PATTERNS:
            match = pattern.match(normalized)
            if not match:
                continue
            prefix = (match.groupdict().get("prefix") or "").title()
            sequence = self._parse_sequence(match.group("sequence"))
            semantic_title = self._normalize_text(match.group("title"))
            return HeadingNormalizationResult(
                original_heading=original,
                normalized_heading=normalized,
                structural_prefix=prefix,
                sequence_number=sequence,
                semantic_title=semantic_title,
                generic_structure=not bool(semantic_title),
                malformed_tokenization=malformed_tokenization,
                metadata=metadata,
            )

        for pattern in self._GENERIC_PATTERNS:
            match = pattern.match(normalized)
            if not match:
                continue
            prefix = (match.groupdict().get("prefix") or "").title()
            sequence_value = match.groupdict().get("sequence") or normalized
            return HeadingNormalizationResult(
                original_heading=original,
                normalized_heading=normalized,
                structural_prefix=prefix,
                sequence_number=self._parse_sequence(sequence_value),
                semantic_title="",
                generic_structure=True,
                malformed_tokenization=malformed_tokenization,
                metadata=metadata,
            )

        return HeadingNormalizationResult(
            original_heading=original,
            normalized_heading=normalized,
            semantic_title=normalized,
            malformed_tokenization=malformed_tokenization,
            metadata=metadata,
        )

    def semantic_key(self, heading: str) -> str:
        normalized = self.normalize(heading)
        base = normalized.semantic_title or normalized.normalized_heading
        base = re.sub(r"^(chapter|section|unit|lesson|topic)\s+", "", base, flags=re.IGNORECASE)
        base = re.sub(r"[^\w\s]", " ", base.lower())
        return re.sub(r"\s+", " ", base).strip()

    def _normalize_text(self, value: str) -> str:
        value = re.sub(r"\s+", " ", (value or "").strip(" \t\r\n-:;,."))
        return value

    def _parse_sequence(self, raw_value: str) -> int | None:
        candidate = raw_value.strip().lower()
        if candidate.isdigit():
            return int(candidate)
        if candidate in self._SEQUENCE_WORDS:
            return self._SEQUENCE_WORDS[candidate]
        if candidate in self._ROMAN_MAP:
            return self._ROMAN_MAP[candidate]
        if re.fullmatch(r"\d+(?:\.\d+)+", candidate):
            return int(candidate.split(".", 1)[0])
        return None

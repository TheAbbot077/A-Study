from __future__ import annotations

from dataclasses import replace
from typing import Any

from apps.content_intelligence.domain.services import ExtractionPayload


def sanitize_extracted_text(value: str | None) -> str:
    if not value:
        return ""
    return value.replace("\x00", "")


def sanitize_text_value(value: Any) -> tuple[Any, int]:
    if isinstance(value, str):
        removed = value.count("\x00")
        return sanitize_extracted_text(value), removed
    if isinstance(value, list):
        sanitized_items: list[Any] = []
        removed_total = 0
        for item in value:
            sanitized_item, removed = sanitize_text_value(item)
            sanitized_items.append(sanitized_item)
            removed_total += removed
        return sanitized_items, removed_total
    if isinstance(value, dict):
        sanitized_mapping: dict[Any, Any] = {}
        removed_total = 0
        for key, item in value.items():
            sanitized_key, key_removed = sanitize_text_value(key)
            sanitized_item, item_removed = sanitize_text_value(item)
            sanitized_mapping[sanitized_key] = sanitized_item
            removed_total += key_removed + item_removed
        return sanitized_mapping, removed_total
    return value, 0


def sanitize_extraction_payload(payload: ExtractionPayload) -> tuple[ExtractionPayload, int]:
    extracted_text, extracted_removed = sanitize_text_value(payload.extracted_text)
    normalized_text, normalized_removed = sanitize_text_value(payload.normalized_text)
    metadata, metadata_removed = sanitize_text_value(payload.metadata)
    removed_total = extracted_removed + normalized_removed + metadata_removed

    if removed_total == 0:
        return payload, 0

    next_metadata = dict(metadata)
    next_metadata["nul_bytes_removed"] = removed_total
    return (
        replace(
            payload,
            extracted_text=extracted_text,
            normalized_text=normalized_text,
            metadata=next_metadata,
        ),
        removed_total,
    )

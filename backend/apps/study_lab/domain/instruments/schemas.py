from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


class InstrumentSchemaError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


MAX_ITEMS = 200
MAX_TEXT = 10_000
ALLOWED_AUTHORS = {
    "LEARNER_AUTHORED",
    "LEARNER_EDITED",
    "TOOL_GENERATED",
    "AI_GENERATED",
    "SOURCE_REFERENCED",
    "MIXED",
}


def _ensure_mapping(value, code: str, message: str):
    if not isinstance(value, dict):
        raise InstrumentSchemaError(code, message)
    return value


def _ensure_list(value, code: str, message: str):
    if not isinstance(value, list):
        raise InstrumentSchemaError(code, message)
    if len(value) > MAX_ITEMS:
        raise InstrumentSchemaError(code, message)
    return value


def _ensure_text(value, code: str, message: str):
    if not isinstance(value, str) or not value.strip():
        raise InstrumentSchemaError(code, message)
    if len(value) > MAX_TEXT:
        raise InstrumentSchemaError(code, message)
    return value


def _validate_unique_ids(items, key="id", code="ARTEFACT_SCHEMA_INVALID"):
    ids = []
    for item in items:
        item_id = item.get(key)
        if not item_id:
            raise InstrumentSchemaError(code, f"Missing {key}.")
        if item_id in ids:
            raise InstrumentSchemaError(code, f"Duplicate {key}.")
        ids.append(item_id)
    return ids


def validate_equation_payload(payload: dict) -> dict:
    payload = _ensure_mapping(payload, "ARTEFACT_SCHEMA_INVALID", "Equation payload must be an object.")
    nodes = _ensure_list(payload.get("nodes", []), "ARTEFACT_SCHEMA_INVALID", "Equation nodes must be a list.")
    _validate_unique_ids(nodes)
    allowed_types = {
        "NUMBER",
        "VARIABLE",
        "OPERATOR",
        "FRACTION",
        "POWER",
        "ROOT",
        "FUNCTION",
        "SUMMATION",
        "INTEGRAL",
        "LIMIT",
        "VECTOR",
        "MATRIX",
        "BRACKET_GROUP",
        "PIECEWISE",
        "SYMBOL",
        "SUBSCRIPT",
        "SUPERSCRIPT",
    }
    for node in nodes:
        node_type = node.get("type")
        if node_type not in allowed_types:
            raise InstrumentSchemaError("ARTEFACT_SCHEMA_INVALID", "Unsupported equation node type.")
    return payload


def validate_formula_sheet_payload(payload: dict) -> dict:
    payload = _ensure_mapping(payload, "ARTEFACT_SCHEMA_INVALID", "Formula sheet payload must be an object.")
    sections = _ensure_list(payload.get("sections", []), "ARTEFACT_SCHEMA_INVALID", "Formula sheet sections must be a list.")
    for section in sections:
        if not section.get("title"):
            raise InstrumentSchemaError("ARTEFACT_SCHEMA_INVALID", "Formula sheet sections need titles.")
    return payload


def validate_diagram_payload(payload: dict) -> dict:
    payload = _ensure_mapping(payload, "ARTEFACT_SCHEMA_INVALID", "Diagram payload must be an object.")
    objects = _ensure_list(payload.get("objects", []), "ARTEFACT_SCHEMA_INVALID", "Diagram objects must be a list.")
    object_ids = _validate_unique_ids(objects)
    for obj in objects:
        refs = obj.get("connection_references", []) or []
        for ref in refs:
            if ref not in object_ids:
                raise InstrumentSchemaError("ARTEFACT_REFERENCE_INVALID", "Dangling diagram reference.")
        author = obj.get("authorship")
        if author and author not in ALLOWED_AUTHORS:
            raise InstrumentSchemaError("ARTEFACT_SCHEMA_INVALID", "Invalid diagram authorship.")
    return payload


def validate_graph_payload(payload: dict) -> dict:
    payload = _ensure_mapping(payload, "ARTEFACT_SCHEMA_INVALID", "Graph payload must be an object.")
    expressions = _ensure_list(payload.get("expressions", []), "ARTEFACT_SCHEMA_INVALID", "Graph expressions must be a list.")
    if not expressions:
        raise InstrumentSchemaError("ARTEFACT_SCHEMA_INVALID", "At least one graph expression is required.")
    return payload


def validate_concept_map_payload(payload: dict) -> dict:
    payload = _ensure_mapping(payload, "ARTEFACT_SCHEMA_INVALID", "Concept map payload must be an object.")
    nodes = _ensure_list(payload.get("nodes", []), "ARTEFACT_SCHEMA_INVALID", "Concept map nodes must be a list.")
    relationships = _ensure_list(payload.get("relationships", []), "ARTEFACT_SCHEMA_INVALID", "Concept map relationships must be a list.")
    node_ids = _validate_unique_ids(nodes)
    for rel in relationships:
        if rel.get("source") not in node_ids or rel.get("target") not in node_ids:
            raise InstrumentSchemaError("ARTEFACT_REFERENCE_INVALID", "Invalid concept map reference.")
    return payload


def validate_timeline_payload(payload: dict) -> dict:
    payload = _ensure_mapping(payload, "ARTEFACT_SCHEMA_INVALID", "Timeline payload must be an object.")
    events = _ensure_list(payload.get("events", []), "ARTEFACT_SCHEMA_INVALID", "Timeline events must be a list.")
    previous = None
    for event in events:
        stamp = event.get("date") or event.get("position")
        if stamp is None:
            raise InstrumentSchemaError("ARTEFACT_SCHEMA_INVALID", "Timeline events need a date or position.")
        if previous is not None and isinstance(stamp, str) and isinstance(previous, str) and stamp < previous:
            raise InstrumentSchemaError("ARTEFACT_SCHEMA_INVALID", "Timeline events must be ordered.")
        previous = stamp
    return payload


def validate_comparison_table_payload(payload: dict) -> dict:
    payload = _ensure_mapping(payload, "ARTEFACT_SCHEMA_INVALID", "Comparison table payload must be an object.")
    rows = _ensure_list(payload.get("rows", []), "ARTEFACT_SCHEMA_INVALID", "Comparison table rows must be a list.")
    if not payload.get("criteria") or not payload.get("subjects"):
        raise InstrumentSchemaError("ARTEFACT_SCHEMA_INVALID", "Comparison tables need subjects and criteria.")
    return payload


def validate_flashcard_payload(payload: dict) -> dict:
    payload = _ensure_mapping(payload, "ARTEFACT_SCHEMA_INVALID", "Flashcard payload must be an object.")
    cards = _ensure_list(payload.get("cards", []), "ARTEFACT_SCHEMA_INVALID", "Flashcards must be a list.")
    for index, card in enumerate(cards):
        _ensure_text(card.get("front", ""), "ARTEFACT_SCHEMA_INVALID", f"Flashcard {index + 1} front is required.")
        _ensure_text(card.get("back", ""), "ARTEFACT_SCHEMA_INVALID", f"Flashcard {index + 1} back is required.")
        author = card.get("authorship", "LEARNER_AUTHORED")
        if author not in ALLOWED_AUTHORS:
            raise InstrumentSchemaError("ARTEFACT_SCHEMA_INVALID", "Invalid flashcard authorship.")
    return payload


def validate_scratchpad_payload(payload: dict) -> dict:
    payload = _ensure_mapping(payload, "ARTEFACT_SCHEMA_INVALID", "Scratchpad payload must be an object.")
    blocks = _ensure_list(payload.get("blocks", []), "ARTEFACT_SCHEMA_INVALID", "Scratchpad blocks must be a list.")
    for block in blocks:
        if block.get("type") not in {"TEXT", "NUMBER", "EQUATION", "TABLE_REFERENCE", "GRAPH_REFERENCE", "DIAGRAM_REFERENCE", "CHECKLIST"}:
            raise InstrumentSchemaError("ARTEFACT_SCHEMA_INVALID", "Unsupported scratchpad block type.")
    return payload


def validate_code_payload(payload: dict) -> dict:
    payload = _ensure_mapping(payload, "ARTEFACT_SCHEMA_INVALID", "Code payload must be an object.")
    _ensure_text(payload.get("language", ""), "CODE_LANGUAGE_NOT_SUPPORTED", "Code language is required.")
    _ensure_text(payload.get("source", ""), "ARTEFACT_SCHEMA_INVALID", "Code source is required.")
    if len(payload["source"]) > MAX_TEXT:
        raise InstrumentSchemaError("ARTEFACT_SCHEMA_INVALID", "Code source too large.")
    return payload

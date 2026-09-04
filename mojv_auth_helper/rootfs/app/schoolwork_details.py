"""Safe helpers for enriching schoolwork list rows with detail payloads."""
from __future__ import annotations

from typing import Any

_SAFE_DETAIL_KEYS = {
    "id",
    "typ",
    "data",
    "terminOdpowiedzi",
    "przedmiotNazwa",
    "temat",
    "nazwa",
    "opis",
    "tresc",
    "nauczycielImieNazwisko",
}


def _detail_dict(payload: Any) -> dict[str, Any]:
    current = payload
    for _ in range(3):
        if not isinstance(current, dict):
            return {}
        nested = current.get("data")
        if isinstance(nested, dict):
            current = nested
            continue
        nested = current.get("result")
        if isinstance(nested, dict):
            current = nested
            continue
        break
    return current if isinstance(current, dict) else {}


def schoolwork_rows(payload: Any) -> list[dict[str, Any]]:
    """Return mutable list rows from common response envelopes."""
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("data", "result", "items"):
            rows = payload.get(key)
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)]
    return []


def detail_endpoint(row: dict[str, Any]) -> str | None:
    """Select the detail endpoint for a schoolwork list row."""
    try:
        type_id = int(row.get("typ") or 0)
    except (TypeError, ValueError):
        return None
    if type_id == 4:
        return "ZadanieDomoweSzczegoly"
    if type_id in {1, 2, 3}:
        return "SprawdzianSzczegoly"
    return None


def needs_detail(row: dict[str, Any]) -> bool:
    """Return whether a supported row must be enriched from its detail endpoint."""
    return row.get("id") is not None and detail_endpoint(row) is not None


def merge_schoolwork_detail(
    row: dict[str, Any],
    payload: Any,
) -> dict[str, Any]:
    """Merge only display-safe fields from a detail response."""
    merged = dict(row)
    detail = _detail_dict(payload)
    for key in _SAFE_DETAIL_KEYS:
        if key in detail:
            merged[key] = detail[key]
    return merged

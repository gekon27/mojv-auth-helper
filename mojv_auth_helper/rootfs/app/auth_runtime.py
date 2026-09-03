"""Pure runtime primitives for the local mojV browser helper."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any


@dataclass(frozen=True, slots=True)
class StudentTarget:
    """Internal routing data kept only inside the helper process."""

    student_id: str
    name: str
    class_name: str
    city: str
    app_url: str
    session_key: str
    journal_id: str = ""

    def public_dict(self) -> dict[str, str]:
        """Return the secret-free student descriptor consumed by Home Assistant."""
        return {
            "student_id": self.student_id,
            "name": self.name,
            "class_name": self.class_name,
        }


def credential_cache_key(username: str, password: str) -> str:
    """Create a non-reversible in-memory cache key bound to both credentials."""
    normalized_username = username.strip().lower()
    material = f"{normalized_username}\0{password}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def unwrap_context(payload: Any) -> Any:
    """Unwrap common JSON envelopes until the journal context is reached."""
    current = payload
    for _ in range(4):
        if not isinstance(current, dict):
            return current
        data = current.get("data")
        if isinstance(data, dict):
            current = data
            continue
        result = current.get("result")
        if isinstance(result, dict):
            current = result
            continue
        return current
    return current


def targets_from_context(
    city: str,
    app_url: str,
    payload: Any,
) -> tuple[StudentTarget, ...]:
    """Extract every usable student from one authenticated context response."""
    context = unwrap_context(payload)
    if not isinstance(context, dict):
        return ()
    rows = context.get("uczniowie")
    if not isinstance(rows, list):
        return ()

    targets: list[StudentTarget] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        key = str(row.get("key") or "").strip()
        name = str(row.get("uczen") or row.get("nazwa") or "").strip()
        if not key or not name:
            continue
        class_name = str(row.get("oddzial") or row.get("klasa") or "").strip()
        journal_id = str(row.get("idDziennik") or "").strip()
        raw_id = (
            row.get("idUczen")
            or row.get("idUcznia")
            or row.get("id")
            or row.get("idDziennik")
        )
        student_id = str(raw_id or f"{city}:{class_name}:{name}")
        unique = f"{city}:{student_id}:{key}"
        if unique in seen:
            continue
        seen.add(unique)
        targets.append(
            StudentTarget(
                student_id=student_id,
                name=name,
                class_name=class_name,
                city=city,
                app_url=app_url,
                session_key=key,
                journal_id=journal_id,
            )
        )
    return tuple(targets)


def public_snapshot_row(
    target: StudentTarget,
    *,
    timetable: Any,
    attendance: Any,
    classification_periods: Any = None,
    grades_by_period: dict[str, Any] | None = None,
    schoolwork: Any = None,
    errors: dict[str, str],
) -> dict[str, Any]:
    """Build one helper response row without any authentication material."""
    return {
        **target.public_dict(),
        "timetable": timetable,
        "attendance": attendance,
        "classification_periods": classification_periods,
        "grades_by_period": dict(grades_by_period or {}),
        "schoolwork": schoolwork,
        "errors": dict(errors),
    }

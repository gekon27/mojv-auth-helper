from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "mojv_auth_helper" / "rootfs" / "app"


def _load_runtime():
    path = APP / "auth_runtime.py"
    spec = importlib.util.spec_from_file_location("mojv_helper_auth_runtime_expanded_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_public_snapshot_row_carries_safe_expanded_modules_only() -> None:
    runtime = _load_runtime()
    target = runtime.StudentTarget(
        student_id="1",
        name="Test",
        class_name="5A",
        city="gryfino",
        app_url="https://student.example/App",
        session_key="SESSION_SECRET",
        journal_id="JOURNAL_SECRET",
        mailbox_key="MAILBOX_SECRET",
    )
    row = runtime.public_snapshot_row(
        target,
        timetable=[],
        attendance=[],
        lucky_number={"numer": 20},
        free_days=[],
        excuses={"usprawiedliwieniaAktywne": True, "usprawiedliwienia": []},
        teachers={"nauczyciele": [{"imieNazwisko": "A. Teacher", "globalKeySkrzynka": "TEACHER_SECRET"}]},
        school_info={"nazwa": "Szkoła"},
        important_today=[],
        homeroom_teachers=[{"imieNazwisko": "Jan Kowalski", "isGlowny": True, "globalKeySkrzynka": "HOMEROOM_SECRET"}],
        completed_lessons=[],
        errors={},
    )

    for key in (
        "lucky_number",
        "free_days",
        "excuses",
        "teachers",
        "school_info",
        "important_today",
        "homeroom_teachers",
        "completed_lessons",
    ):
        assert key in row
    serialized = repr(row)
    for secret in (
        "SESSION_SECRET",
        "JOURNAL_SECRET",
        "MAILBOX_SECRET",
        "TEACHER_SECRET",
        "HOMEROOM_SECRET",
    ):
        assert secret not in serialized
    assert "globalKeySkrzynka" not in serialized


def test_server_live_fetches_all_expanded_read_only_endpoints() -> None:
    source = (APP / "server_live.py").read_text(encoding="utf-8")
    for endpoint in (
        "DniWolne",
        "Usprawiedliwienia",
        "Nauczyciele",
        "Informacje",
        "SzczesliwyNumerTablica",
        "WazneDzisiajTablica",
        "WychowawcyTablica",
        "RealizacjaZajec",
    ):
        assert f'"{endpoint}"' in source, endpoint
    assert '"status": 1' in source


def test_helper_source_does_not_export_sensitive_student_profile() -> None:
    source = (APP / "server_live.py").read_text(encoding="utf-8").lower()
    assert "daneucznia" not in source
    assert "uczenzdjecie" not in source

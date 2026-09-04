from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "mojv_auth_helper" / "rootfs" / "app" / "auth_runtime.py"
SERVER = ROOT / "mojv_auth_helper" / "rootfs" / "app" / "server.py"
LIVE_SERVER = ROOT / "mojv_auth_helper" / "rootfs" / "app" / "server_live.py"
DOCKERFILE = ROOT / "mojv_auth_helper" / "Dockerfile"
RUN_SCRIPT = ROOT / "mojv_auth_helper" / "rootfs" / "etc" / "services.d" / "mojv-auth" / "run"


def _load():
    assert MODULE.exists(), "auth_runtime.py must implement browser helper parsing"
    spec = importlib.util.spec_from_file_location("mojv_auth_runtime_test", MODULE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_unwrap_context_accepts_nested_data_and_result() -> None:
    runtime = _load()
    payload = {"result": "ok", "data": {"uczniowie": [{"uczen": "Jan"}]}}
    assert runtime.unwrap_context(payload) == {"uczniowie": [{"uczen": "Jan"}]}


def test_context_rows_become_internal_targets_without_secret_in_public_row() -> None:
    runtime = _load()
    targets = runtime.targets_from_context(
        "gryfino",
        "https://uczen.example/gryfino/App/abc/tablica",
        {
            "uczniowie": [
                {
                    "idUczen": 12,
                    "idDziennik": 99,
                    "uczen": "Jan Kowalski",
                    "oddzial": "5A",
                    "key": "SECRET-KEY",
                    "globalKeySkrzynka": "MAILBOX-SECRET",
                }
            ]
        },
    )
    assert len(targets) == 1
    target = targets[0]
    assert target.session_key == "SECRET-KEY"
    assert target.journal_id == "99"
    assert target.mailbox_key == "MAILBOX-SECRET"
    assert target.public_dict() == {
        "student_id": "12",
        "name": "Jan Kowalski",
        "class_name": "5A",
    }
    public = str(target.public_dict())
    assert "SECRET" not in public
    assert "99" not in public


def test_snapshot_student_never_contains_browser_or_session_secrets() -> None:
    runtime = _load()
    target = runtime.StudentTarget(
        student_id="12",
        name="Jan",
        class_name="5A",
        city="gryfino",
        app_url="https://uczen.example/gryfino/App/abc/tablica",
        session_key="SECRET",
        journal_id="99",
        mailbox_key="MAILBOX-SECRET",
    )
    row = runtime.public_snapshot_row(
        target,
        timetable=[],
        attendance=[],
        attendance_subjects=[],
        attendance_summary={},
        attendance_by_subject={},
        classification_periods=[{"id": 1, "numerOkresu": 1}],
        grades_by_period={"1": {"ocenyPrzedmioty": []}},
        remarks=[],
        schoolwork=[{"id": 7, "typ": 4}],
        messages=[],
        message_details={},
        achievements=[],
        meetings=[],
        lucky_number={"numer": 20},
        free_days=[],
        excuses={"usprawiedliwieniaAktywne": True, "usprawiedliwienia": []},
        teachers={"nauczyciele": []},
        school_info={"nazwa": "Szkoła"},
        important_today=[],
        homeroom_teachers=[],
        completed_lessons=[],
        errors={},
    )
    assert set(row) == {
        "student_id",
        "name",
        "class_name",
        "timetable",
        "attendance",
        "attendance_subjects",
        "attendance_summary",
        "attendance_by_subject",
        "classification_periods",
        "grades_by_period",
        "remarks",
        "schoolwork",
        "messages",
        "message_details",
        "achievements",
        "meetings",
        "lucky_number",
        "free_days",
        "excuses",
        "teachers",
        "school_info",
        "important_today",
        "homeroom_teachers",
        "completed_lessons",
        "errors",
    }
    public = str(row)
    assert "SECRET" not in public
    assert "'journal_id'" not in public
    assert "'session_key'" not in public
    assert "'mailbox_key'" not in public
    assert "'globalKeySkrzynka'" not in public
    assert "'apiGlobalKey'" not in public


def test_browser_cache_key_is_bound_to_both_username_and_password() -> None:
    runtime = _load()
    first = runtime.credential_cache_key("Parent", "secret-one")
    same = runtime.credential_cache_key(" parent ", "secret-one")
    wrong_password = runtime.credential_cache_key("Parent", "secret-two")

    assert first == same
    assert first != wrong_password
    assert "Parent" not in first
    assert "secret-one" not in first


def test_browser_runs_inside_xvfb_with_classic_headless_mode() -> None:
    server = SERVER.read_text(encoding="utf-8")
    dockerfile = DOCKERFILE.read_text(encoding="utf-8").lower()
    run_script = RUN_SCRIPT.read_text(encoding="utf-8")

    assert '--headless=new' not in server
    assert 'options.add_argument("--headless")' in server
    assert 'xvfb' in dockerfile
    assert 'Xvfb' in run_script
    assert 'DISPLAY=' in run_script
    assert 'server_live.py' in run_script


def test_helper_logs_safe_auth_stages_and_redacted_screenshot() -> None:
    server = SERVER.read_text(encoding="utf-8")

    for stage in (
        "login-page",
        "username-submitted",
        "password-submitted",
        "diary-links",
        "student-app",
        "context",
    ):
        assert stage in server
    assert "mojv_auth_error.png" in server
    assert "input.value = ''" in server or 'input.value = ""' in server


def test_helper_health_version_comes_from_image_build_version() -> None:
    server = SERVER.read_text(encoding="utf-8")
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")

    assert 'MOJV_HELPER_VERSION' in server
    assert 'MOJV_HELPER_VERSION' in dockerfile


def test_diary_link_renderer_timeout_is_recovered_per_link() -> None:
    server = SERVER.read_text(encoding="utf-8")

    assert "def _open_diary_link" in server
    assert "Auth stage=diary-link-load-timeout" in server
    assert "window.stop()" in server
    assert "for index, link in enumerate(links, start=1)" in server
    assert "link_failures" in server


def test_helper_snapshot_fetches_extended_live_modules() -> None:
    server = SERVER.read_text(encoding="utf-8") + LIVE_SERVER.read_text(encoding="utf-8")

    for marker in (
        "zakresDanych",
        "SprawdzianyZadaniaDomowe",
        "OkresyKlasyfikacyjne",
        "Oceny",
        "Przedmioty",
        "FrekwencjaStatystyki",
        "Uwagi",
        "Osiagniecia",
        "Zebrania",
        "OdebraneSkrzynka",
        "WiadomoscSzczegoly",
        "DniWolne",
        "Usprawiedliwienia",
        "Nauczyciele",
        "Informacje",
        "SzczesliwyNumerTablica",
        "WazneDzisiajTablica",
        "WychowawcyTablica",
        "RealizacjaZajec",
    ):
        assert marker in server


def test_message_routing_ids_are_sanitized_before_public_snapshot() -> None:
    live = LIVE_SERVER.read_text(encoding="utf-8")

    assert "_public_message_id" in live
    assert "hashlib.sha256" in live
    assert '"apiglobalkey"' in live.lower()
    assert '"globalkeyskrzynka"' in live.lower()
    assert "target.mailbox_key" in live

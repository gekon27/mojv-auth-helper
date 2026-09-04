from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "mojv_auth_helper" / "rootfs" / "app"
DETAILS = APP / "schoolwork_details.py"
SERVER_LIVE = APP / "server_live.py"


def _load_details():
    assert DETAILS.exists(), "schoolwork detail helper is not implemented yet"
    spec = importlib.util.spec_from_file_location("mojv_helper_schoolwork_details", DETAILS)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_homework_and_exam_detail_endpoints_are_selected_by_type() -> None:
    module = _load_details()
    assert module.detail_endpoint({"id": 1, "typ": 4}) == "ZadanieDomoweSzczegoly"
    assert module.detail_endpoint({"id": 2, "typ": 1}) == "SprawdzianSzczegoly"
    assert module.detail_endpoint({"id": 3, "typ": 2}) == "SprawdzianSzczegoly"
    assert module.detail_endpoint({"id": 4, "typ": 3}) == "SprawdzianSzczegoly"
    assert module.detail_endpoint({"id": 5, "typ": 0}) is None


def test_supported_schoolwork_still_needs_detail_when_list_has_preview() -> None:
    module = _load_details()
    assert module.needs_detail({"id": 101, "typ": 4, "opis": "Skrót z listy."}) is True
    assert module.needs_detail({"id": 102, "typ": 1, "tresc": "Krótki podgląd."}) is True


def test_detail_merge_keeps_homework_description_and_drops_private_fields() -> None:
    module = _load_details()
    row = {"id": 101, "typ": 4, "przedmiotNazwa": "Matematyka", "opis": "Skrót z listy."}
    detail = {
        "id": 101,
        "typ": 4,
        "opis": "Zrób zadania 1-5 ze strony 42.",
        "terminOdpowiedzi": "2026-09-10T00:00:00+02:00",
        "globalKeySkrzynka": "secret-routing",
        "odpowiedzUcznia": "private-answer",
        "plikiOdpowiedziUcznia": [{"nazwa": "private.txt"}],
    }

    merged = module.merge_schoolwork_detail(row, detail)

    assert merged["opis"] == "Zrób zadania 1-5 ze strony 42."
    assert merged["terminOdpowiedzi"] == "2026-09-10T00:00:00+02:00"
    assert "globalKeySkrzynka" not in merged
    assert "odpowiedzUcznia" not in merged
    assert "plikiOdpowiedziUcznia" not in merged


def test_browser_fallback_enriches_schoolwork_before_public_snapshot() -> None:
    source = SERVER_LIVE.read_text(encoding="utf-8")
    assert "detail_endpoint" in source
    assert "merge_schoolwork_detail" in source
    assert '"schoolwork_detail:' in source
    schoolwork_index = source.index('"SprawdzianyZadaniaDomowe"')
    public_index = source.index("base.public_snapshot_row(")
    detail_index = source.index("merge_schoolwork_detail", schoolwork_index)
    assert schoolwork_index < detail_index < public_index

"""Browser fallback timetable horizon contract."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER_LIVE = ROOT / "mojv_auth_helper" / "rootfs" / "app" / "server_live.py"


def test_browser_fallback_uses_same_four_week_timetable_window() -> None:
    source = SERVER_LIVE.read_text(encoding="utf-8")

    assert "week_start = now - timedelta(days=now.weekday())" in source
    assert "date_from = week_start - timedelta(weeks=1)" in source
    assert "date_to = week_start + timedelta(weeks=5, days=-1)" in source
    assert "now + timedelta(days=21)" not in source

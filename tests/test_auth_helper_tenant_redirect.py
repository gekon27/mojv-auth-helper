from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "mojv_auth_helper" / "rootfs" / "app" / "server.py"


def test_student_redirect_accepts_tenant_host_without_app_path() -> None:
    """A valid student-tenant redirect must not require an /App/ path."""
    server = SERVER.read_text(encoding="utf-8")

    assert "def _wait_for_student_tenant" in server
    assert 'parsed.netloc.lower() == _STUDENT_HOST' in server
    assert '"/app/" in parsed.path.lower()' not in server
    assert "return _wait_for_student_tenant(" in server

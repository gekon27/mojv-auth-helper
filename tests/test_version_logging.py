from pathlib import Path


def test_helper_startup_logs_runtime_version() -> None:
    source = Path(
        "mojv_auth_helper/rootfs/etc/services.d/mojv-auth/run"
    ).read_text(encoding="utf-8")
    assert "mojV Auth Helper version=" in source
    assert "MOJV_HELPER_VERSION" in source

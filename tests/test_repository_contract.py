from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "mojv_auth_helper"
EXPECTED_VERSION = "0.1.10"
EXPECTED_REPO = "https://github.com/gekon27/mojv-auth-helper"
EXPECTED_IMAGE = "ghcr.io/gekon27/mojv-auth-helper"


def _yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_repository_metadata_points_to_standalone_repo() -> None:
    repository = _yaml(ROOT / "repository.yaml")
    assert repository["url"] == EXPECTED_REPO
    assert repository["maintainer"] == "gekon27"


def test_app_metadata_is_consistent_and_multiarch() -> None:
    config = _yaml(APP / "config.yaml")
    build = _yaml(APP / "build.yaml")

    assert config["slug"] == "mojv_auth_helper"
    assert config["version"] == EXPECTED_VERSION
    assert config["url"] == EXPECTED_REPO
    assert config["image"] == EXPECTED_IMAGE
    assert set(config["arch"]) == {"amd64", "aarch64"}
    assert set(build["build_from"]) == {"amd64", "aarch64"}


def test_container_contract_exposes_build_version_and_base_override() -> None:
    dockerfile = (APP / "Dockerfile").read_text(encoding="utf-8")
    run_script = (APP / "rootfs/etc/services.d/mojv-auth/run").read_text(encoding="utf-8")
    server = (APP / "rootfs/app/server.py").read_text(encoding="utf-8")

    assert "ARG BUILD_FROM=" in dockerfile
    assert "FROM ${BUILD_FROM}" in dockerfile
    assert "ARG BUILD_VERSION" in dockerfile
    assert 'MOJV_HELPER_VERSION="${BUILD_VERSION}"' in dockerfile
    assert "MOJV_HELPER_VERSION" in run_script
    assert "MOJV_HELPER_VERSION" in server
    assert '"/health"' in server
    assert "server_live.py" in run_script


def test_docs_describe_installation_fallback_and_security_boundary() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    docs = (APP / "DOCS.md").read_text(encoding="utf-8")
    changelog = (APP / "CHANGELOG.md").read_text(encoding="utf-8")
    combined = "\n".join((readme, docs))

    assert EXPECTED_REPO in combined
    assert "https://github.com/gekon27/mojV" in combined
    assert "HTTP" in combined
    assert "fallback" in combined.lower()
    assert "1..N" in combined or "1…N" in combined
    assert "password" in combined.lower() or "hasła" in combined.lower()
    assert "cookie" in combined.lower()
    assert EXPECTED_VERSION in changelog
    assert EXPECTED_VERSION in combined


def test_publish_workflow_keeps_multiarch_and_anonymous_pull_gates() -> None:
    publish = (ROOT / ".github/workflows/publish.yml").read_text(encoding="utf-8")

    assert "linux/amd64" in publish
    assert "linux/arm64" in publish
    assert "imagetools create" in publish
    assert "docker logout ghcr.io" in publish
    assert "docker pull" in publish

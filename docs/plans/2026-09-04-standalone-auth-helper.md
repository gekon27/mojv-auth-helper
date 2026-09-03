# Standalone mojV Auth Helper repository migration

Date: 2026-09-04

## Goal

Move the working browser-auth helper from `gekon27/mojV` into the dedicated `gekon27/mojv-auth-helper` Home Assistant App repository without changing its authentication contract.

## Hard gates

- mojV remains HTTP-first; helper is automatic fallback only.
- Support 1..N students; never hardcode a child count.
- Never expose password, cookies, tokens, session keys or routing identifiers.
- Chromium + ChromeDriver + Xvfb container must build and run.
- `/health` must return the exact image version.
- GHCR must publish `linux/amd64` and `linux/arm64` under one version manifest.
- Anonymous pull of the versioned image must succeed.
- The old helper inside `gekon27/mojV` is removed only after all gates above are green on the standalone repository.

## Verification

1. Contract and regression tests.
2. Python compilation.
3. Native amd64 image build and runtime health check.
4. Xvfb/Chromium/ChromeDriver checks.
5. aarch64 build under QEMU.
6. Multi-arch publish on main.
7. Manifest platform assertion.
8. Logout and anonymous `docker pull`.

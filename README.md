# mojV Auth Helper

Standalone Home Assistant App repository for the browser fallback used by the **mojV** integration.

## What this repository is

`mojV Auth Helper` is a local Chromium/Xvfb service. It is **not** the main Home Assistant integration and it is not the preferred transport. The main integration lives at:

- https://github.com/gekon27/mojV

mojV always attempts the lightweight HTTP path first. The helper is an automatic **fallback** only when the school portal requires a full browser session.

## Home Assistant installation

Add this repository to the Home Assistant App Store:

- https://github.com/gekon27/mojv-auth-helper

Then install **mojV Auth Helper** and keep automatic startup enabled. There are no user-configurable options in the helper.

The published image for this release is:

- `ghcr.io/gekon27/mojv-auth-helper:0.1.9`

Supported architectures:

- `amd64`
- `aarch64`

## Runtime contract

The helper:

- runs Chromium with ChromeDriver inside a local Xvfb display,
- discovers **1..N** students from the authenticated account; no fixed child count is assumed,
- keeps routing identifiers, mailbox/session keys, cookies and tokens inside the helper,
- returns only secret-free student data to mojV,
- exposes `/health` with the exact running image version,
- isolates modules so one failed endpoint does not block the remaining school data,
- supports timetable, attendance and per-subject statistics, classification periods, grades, schoolwork, remarks, messages, achievements and meetings,
- additionally fetches days off, attendance excuses, teachers, public school information, the daily lucky number, important-today entries, homeroom teachers and completed lesson topics,
- recursively strips authentication/routing fields from expanded public payloads,
- replaces internal message routing identifiers with stable public hashes before returning message metadata.

The private HTTP service listens on port `8099` inside the Home Assistant app network. The app configuration does not expose that port to the LAN.

## Security boundary

- Passwords are accepted only for the current helper request and are not persisted to disk.
- Passwords, cookies, tokens, session keys, mailbox keys and routing identifiers are never returned in public payloads.
- Sensitive student-profile endpoints and student photos are intentionally not exported.
- Logs contain only safe authentication stages, error classes and locations without query strings.
- If browser authentication fails, `/data/mojv_auth_error.png` may be written locally; form input values are cleared before the screenshot.
- The helper cache uses a SHA-256 credential-derived in-memory key and does not retain the password itself.

## Development and validation

`Validate` runs Python compilation and contract/regression tests, native `amd64` image build, runtime `/health`, Xvfb/Chromium/ChromeDriver checks and a control `aarch64` build through QEMU/Buildx.

`Publish` builds both architectures, publishes a multi-arch manifest to GHCR, verifies the manifest platforms and finally logs out of GHCR and performs an anonymous pull of the versioned image.

See `mojv_auth_helper/DOCS.md` for operator notes and `mojv_auth_helper/CHANGELOG.md` for release history.

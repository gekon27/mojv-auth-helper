# mojV Auth Helper

Lokalny fallback Chromium/Xvfb dla integracji **mojV** w Home Assistant.

mojV zawsze próbuje najpierw lekkiego połączenia HTTP. Ta aplikacja uruchamia pełną przeglądarkę tylko wtedy, gdy portal szkolny wymaga browser-based authentication.

Najważniejsze właściwości:

- automatyczny fallback — bez ręcznego wyboru backendu,
- obsługa 1..N dzieci,
- plan, frekwencja, okresy klasyfikacyjne, oceny oraz terminarz/prace szkolne,
- brak eksportu cookies, tokenów, kluczy sesji i identyfikatorów routingu,
- hasło nie jest zapisywane na dysku,
- Chromium działa lokalnie w Xvfb,
- obrazy `amd64` i `aarch64` publikowane jako jeden manifest multi-arch,
- `/health` raportuje dokładną wersję uruchomionego obrazu.

Integracja HACS: https://github.com/gekon27/mojV

Repozytorium aplikacji: https://github.com/gekon27/mojv-auth-helper

Szczegóły instalacji i bezpieczeństwa znajdują się w `DOCS.md`.

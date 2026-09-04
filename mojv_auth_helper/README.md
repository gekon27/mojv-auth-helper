# mojV Auth Helper

Lokalny fallback Chromium/Xvfb dla integracji **mojV** w Home Assistant.

mojV zawsze próbuje najpierw lekkiego połączenia HTTP. Ta aplikacja uruchamia pełną przeglądarkę tylko wtedy, gdy portal szkolny wymaga browser-based authentication.

Najważniejsze właściwości:

- automatyczny fallback — bez ręcznego wyboru backendu,
- obsługa 1..N dzieci,
- plan, frekwencja i statystyki per przedmiot, okresy klasyfikacyjne, oceny, terminarz/prace szkolne, uwagi/pochwały, wiadomości, osiągnięcia i zebrania,
- plan obejmuje poprzedni tydzień, tydzień bieżący i 4 pełne tygodnie do przodu,
- dodatkowo: dni wolne, usprawiedliwienia, nauczyciele, publiczne informacje o szkole, szczęśliwy numerek, ważne dzisiaj, wychowawcy i zrealizowane tematy lekcji,
- brak eksportu cookies, tokenów, kluczy sesji, mailbox keys i identyfikatorów routingu,
- rekurencyjne filtrowanie rozszerzonych danych przed wysłaniem do Home Assistant,
- identyfikatory wiadomości zwracane do Home Assistant są hashowane,
- wrażliwy profil ucznia i zdjęcie ucznia nie są eksportowane,
- hasło nie jest zapisywane na dysku,
- Chromium działa lokalnie w Xvfb,
- obrazy `amd64` i `aarch64` publikowane jako jeden manifest multi-arch,
- `/health` raportuje dokładną wersję uruchomionego obrazu.

Wersja aplikacji: **0.1.10**.

Integracja HACS: https://github.com/gekon27/mojV

Repozytorium aplikacji: https://github.com/gekon27/mojv-auth-helper

Szczegóły instalacji i bezpieczeństwa znajdują się w `DOCS.md`.

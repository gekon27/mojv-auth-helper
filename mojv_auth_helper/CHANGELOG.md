# Changelog

## [0.1.11] - 2026-09-04

- plan browser fallback obejmuje teraz dokładnie 4 tygodnie łącznie: poprzedni, bieżący oraz dwa pełne tygodnie do przodu,
- zadania domowe i sprawdziany są wzbogacane o bezpieczny opis z endpointu szczegółowego, gdy wpis listy nie zawiera treści,
- szczegóły są scalane przez whitelistę pól przeznaczonych do wyświetlania; odpowiedzi ucznia, pliki odpowiedzi i pola routingu/uwierzytelnienia nie są eksportowane,
- zachowano HTTP-first / Chromium-fallback parity, izolację błędów oraz obsługę 1..N dzieci.

## [0.1.10] - 2026-09-04

- rozszerzono zakres planu lekcji w browser fallback do poprzedniego tygodnia, tygodnia bieżącego oraz czterech pełnych tygodni do przodu,
- zakres dat planu jest zgodny z bezpośrednią ścieżką HTTP w mojV Core,
- zachowano pojedynczy request planu na ucznia oraz dotychczasową izolację błędów i obsługę 1..N dzieci,
- nie zmieniono granicy bezpieczeństwa: klucze sesji, cookies, tokeny i identyfikatory routingu pozostają wewnątrz helpera.

## [0.1.9] - 2026-09-04

- rozszerzono browser fallback o dni wolne, usprawiedliwienia, nauczycieli, publiczne informacje o szkole, szczęśliwy numerek, wpisy „ważne dzisiaj”, wychowawców i zrealizowane tematy lekcji,
- zachowano niezależne pobieranie modułów i obsługę 1..N dzieci,
- dodano rekurencyjne filtrowanie rozszerzonych payloadów przed ich zwróceniem do Home Assistant,
- pola uwierzytelnienia, mailbox/session keys i identyfikatory routingu pozostają wyłącznie wewnątrz helpera,
- wrażliwy profil ucznia i zdjęcie ucznia nie są eksportowane,
- zachowano dotychczasowe hashowanie publicznych identyfikatorów wiadomości oraz HTTP-first / Chromium-fallback contract.

## [0.1.8] - 2026-09-04

- rozszerzono browser fallback do tego samego kontraktu LIVE co bezpośredni HTTP: uwagi/pochwały, wiadomości, osiągnięcia, zebrania oraz rozszerzone statystyki frekwencji,
- dodano pobieranie `/api/Przedmioty` i `/api/FrekwencjaStatystyki` łącznie ze statystykami per przedmiot,
- dodano `/api/Uwagi`, `/api/Osiagniecia` i `/api/Zebrania`,
- dodano osobny tenant wiadomości z `/api/OdebraneSkrzynka` i `/api/WiadomoscSzczegoly`,
- `globalKeySkrzynka`, klucze sesji i identyfikatory routingu wiadomości pozostają wyłącznie wewnątrz helpera; publiczne ID wiadomości jest hashowane,
- zachowano izolację błędów per moduł, obsługę 1..N dzieci i dotychczasowy browser login flow.

## [0.1.7] - 2026-09-04

- przeniesiono helper do dedykowanego repozytorium `gekon27/mojv-auth-helper`,
- dodano kompletne metadane Home Assistant App Store (`repository.yaml`, `config.yaml`, `build.yaml`),
- zachowano runtime 0.1.6 bez zmiany kontraktu logowania i pobierania danych,
- dodano walidację testów, kompilacji Pythona, uruchomienia obrazu, `/health`, Xvfb, Chromium i ChromeDriver,
- dodano build kontrolny `aarch64`,
- dodano niezależny workflow publikujący obrazy `amd64` i `aarch64` do GHCR jako manifest multi-arch,
- publikacja sprawdza platformy manifestu i anonimowy pull bez poświadczeń GitHub,
- dokumentacja instalacji wskazuje nowe repo App Store; HACS pozostaje w `gekon27/mojV`.

## [0.1.6] - 2026-09-03

- rozszerzony publiczny snapshot helpera o okresy klasyfikacyjne, oceny i terminarz/prace szkolne,
- plan lekcji pobiera pełny zakres danych wymagany przez aktualny endpoint,
- identyfikator dziennika pozostaje wyłącznie wewnątrz helpera i nie jest zwracany do Home Assistant,
- każdy moduł danych jest izolowany: awaria ocen lub terminarza nie blokuje planu i frekwencji,
- diagnostyka modułów zwraca wyłącznie typ błędu bez URL, parametrów zapytania i sekretów,
- Core rekurencyjnie odrzuca payload zawierający pola tokenów, cookies, kluczy sesji lub identyfikatory routingu uwierzytelnienia.

## [0.1.5] - 2026-09-03

- helper zapisuje przy starcie `mojV Auth Helper version=<wersja>`,
- numer wersji pochodzi z `MOJV_HELPER_VERSION`, czyli z dokładnie uruchomionego obrazu,
- log startowy nie zawiera loginu, hasła, cookies ani tokenów.

## [0.1.4] - 2026-09-03

- poprawiono przejście z dashboardu do dziennika: helper akceptuje poprawne przekierowanie na host ucznia bez wymagania ścieżki `/App/...`,
- tenant/miasto jest wykrywane z pierwszego segmentu ścieżki po przekierowaniu SSO,
- wolne ładowanie strony nadal jest izolowane per link, a diagnostyka błędu zawiera bezpieczną lokalizację bez query string i sekretów,
- zachowano obsługę 1..N dzieci i filtrowanie duplikatów.

## [0.1.3] - 2026-09-03

- timeout renderera podczas otwierania pojedynczego linku dziennika nie przerywa już całego logowania,
- helper próbuje zatrzymać niedokończone ładowanie przez `window.stop()` i sprawdza, czy aplikacja ucznia jest już dostępna,
- poprawnie zachowuje wcześniej wykryte konteksty i uczniów, nawet gdy kolejny link jest wolny lub uszkodzony,
- błędy Selenium są zamieniane na kontrolowany błąd helpera zamiast surowej odpowiedzi HTTP 500,
- diagnostyka loguje wyłącznie indeks linku, typ błędu i bezpieczną lokalizację bez sekretów.

## [0.1.2] - 2026-09-03

- uruchamianie Chromium z Xvfb i klasycznym `--headless`,
- dodane etapy diagnostyczne logowania bez zapisywania loginu, hasła, cookies ani query string,
- dodany lokalny screenshot błędu z wyczyszczonymi wartościami pól formularza,
- `/health` raportuje faktyczną wersję obrazu przez `MOJV_HELPER_VERSION`,
- CI sprawdza Xvfb, Chromium i zgodność wersji helpera.

## [0.1.1] - 2026-09-03

- helper jest publikowany jako gotowy wieloarchitekturowy obraz GHCR,
- Home Assistant pobiera obraz zamiast budować go lokalnie,
- obsługa `amd64` i `aarch64`,
- zweryfikowane anonimowe pobieranie obrazu bez tokenu GitHub.

## [0.1.0] - 2026-09-03

- pierwsza wersja lokalnego helpera Chromium dla mojV,
- wykrywanie 1..N dzieci w uwierzytelnionej sesji,
- pobieranie planu lekcji i frekwencji bez eksportowania cookies lub kluczy sesji,
- prywatne API dostępne wyłącznie w wewnętrznej sieci Home Assistant,
- cache sesji powiązany z fingerprintem loginu i hasła,
- brak zapisu hasła na dysku.

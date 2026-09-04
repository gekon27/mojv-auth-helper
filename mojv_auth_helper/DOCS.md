# mojV Auth Helper

Ten komponent jest lokalnym pomocnikiem logowania dla integracji **mojV**.

## Rola

Jego zadania to:

- uruchomić lokalny Chromium, gdy portal szkolny wymaga pełnej przeglądarki,
- utrzymać sesję przeglądarkową wyłącznie wewnątrz kontenera,
- wykrywać 1..N dzieci bez założenia stałej liczby kont ucznia,
- zwrócić integracji mojV wyłącznie bezpieczne dane szkolne potrzebne do encji, automatyzacji i panelu.

Helper obsługuje plan lekcji, frekwencję i statystyki per przedmiot, okresy klasyfikacyjne, oceny, terminarz/prace szkolne, uwagi/pochwały, wiadomości, osiągnięcia i zebrania. W wersji **0.1.9** kontrakt rozszerzono o dni wolne, usprawiedliwienia, nauczycieli, publiczne informacje o szkole, szczęśliwy numerek, wpisy „ważne dzisiaj”, wychowawców i zrealizowane tematy lekcji.

Helper nie jest wymagany dla każdego konta. mojV zawsze najpierw próbuje lekkiego logowania HTTP. Jeżeli konto wymaga pełnej przeglądarki, integracja automatycznie przełącza się na helper jako fallback; użytkownik nie wybiera backendu ręcznie.

Każdy moduł danych jest pobierany niezależnie. Problem z jednym endpointem nie blokuje planu i pozostałych modułów. Dane rozszerzone przechodzą przez rekurencyjny filtr pól uwierzytelnienia i routingu jeszcze przed zwróceniem snapshotu do Home Assistant. Wewnętrzne identyfikatory routingu wiadomości są zastępowane publicznym hashem.

Wrażliwy profil ucznia, dane adresowe/rodzinne oraz zdjęcie ucznia nie są częścią publicznego kontraktu helpera.

Chromium działa z lokalnym wirtualnym ekranem Xvfb i klasycznym trybem headless. Helper zapisuje do logu wyłącznie bezpieczne etapy logowania i lokalizację strony bez parametrów zapytania.

Przy nieudanym logowaniu może powstać lokalny plik `/data/mojv_auth_error.png`. Przed wykonaniem zrzutu helper czyści wartości wszystkich pól formularza.

Helper **nie zapisuje hasła**, nie eksportuje cookies ani kluczy sesji i nie wystawia portu do sieci LAN. Komunikacja odbywa się wyłącznie w wewnętrznej sieci Home Assistant.

## Instalacja

1. Dodaj `https://github.com/gekon27/mojv-auth-helper` jako repozytorium aplikacji Home Assistant.
2. Zainstaluj lub zaktualizuj **mojV Auth Helper** do wersji **0.1.9** lub nowszej.
3. Uruchom aplikację i pozostaw `Uruchamiaj przy starcie` włączone.
4. W HACS zainstaluj lub zaktualizuj integrację mojV z `https://github.com/gekon27/mojV`.
5. Dodaj konto szkolne w integracji mojV. Integracja sama wybierze HTTP lub helper fallback.

Nie ma żadnych opcji do konfiguracji w samym helperze.

## Diagnostyka

- `/health` zwraca `status=ok` i wersję dokładnie uruchomionego obrazu.
- log startowy ma postać `mojV Auth Helper version=<wersja>`.
- logi nie powinny zawierać loginu, hasła, cookies, tokenów, kluczy sesji, mailbox keys ani parametrów query.

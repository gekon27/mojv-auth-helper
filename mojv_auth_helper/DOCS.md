# mojV Auth Helper

Ten komponent jest lokalnym pomocnikiem logowania dla integracji **mojV**.

## Rola

Jego zadania to:

- uruchomić lokalny Chromium, gdy portal szkolny wymaga pełnej przeglądarki,
- utrzymać sesję przeglądarkową wyłącznie wewnątrz kontenera,
- wykrywać 1..N dzieci bez założenia stałej liczby kont ucznia,
- zwrócić integracji mojV wyłącznie publiczne dane uczniów: plan, frekwencję i statystyki, okresy klasyfikacyjne, oceny, terminarz/prace szkolne, uwagi/pochwały, wiadomości, osiągnięcia i zebrania.

Helper nie jest wymagany dla każdego konta. mojV zawsze najpierw próbuje lekkiego logowania HTTP. Jeżeli konto wymaga pełnej przeglądarki, integracja automatycznie przełącza się na helper jako fallback; użytkownik nie wybiera backendu ręcznie.

Każdy moduł danych jest pobierany niezależnie. Problem z wiadomościami, ocenami lub statystykami nie blokuje planu i pozostałych modułów. Identyfikatory routingu, `globalKeySkrzynka`, klucze sesji, cookies i tokeny pozostają wewnątrz helpera. Wewnętrzne identyfikatory routingu wiadomości są zastępowane publicznym hashem przed zwróceniem danych do Home Assistant.

Chromium działa z lokalnym wirtualnym ekranem Xvfb i klasycznym trybem headless. Helper zapisuje do logu wyłącznie bezpieczne etapy logowania i lokalizację strony bez parametrów zapytania.

Przy nieudanym logowaniu może powstać lokalny plik `/data/mojv_auth_error.png`. Przed wykonaniem zrzutu helper czyści wartości wszystkich pól formularza.

Helper **nie zapisuje hasła**, nie eksportuje cookies ani kluczy sesji i nie wystawia portu do sieci LAN. Komunikacja odbywa się wyłącznie w wewnętrznej sieci Home Assistant.

## Instalacja

1. Dodaj `https://github.com/gekon27/mojv-auth-helper` jako repozytorium aplikacji Home Assistant.
2. Zainstaluj lub zaktualizuj **mojV Auth Helper** do wersji **0.1.8** lub nowszej.
3. Uruchom aplikację i pozostaw `Uruchamiaj przy starcie` włączone.
4. W HACS zainstaluj lub zaktualizuj integrację mojV z `https://github.com/gekon27/mojV`.
5. Dodaj konto szkolne w integracji mojV. Integracja sama wybierze HTTP lub helper fallback.

Nie ma żadnych opcji do konfiguracji w samym helperze.

## Diagnostyka

- `/health` zwraca `status=ok` i wersję dokładnie uruchomionego obrazu.
- log startowy ma postać `mojV Auth Helper version=<wersja>`.
- logi nie powinny zawierać loginu, hasła, cookies, tokenów, kluczy sesji, mailbox keys ani parametrów query.

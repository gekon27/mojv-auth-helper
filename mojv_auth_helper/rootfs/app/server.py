"""Private local HTTP service used by mojV for browser-backed authentication."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import logging
import os
import shutil
import time
from typing import Any
from urllib.parse import urlencode, urlparse

from aiohttp import web
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait

from auth_runtime import (
    StudentTarget,
    credential_cache_key,
    public_snapshot_row,
    targets_from_context,
)

_LOGGER = logging.getLogger("mojv_auth_helper")
_PORTAL_ROOT = "https://edu" + "vulcan.pl"
_STUDENT_HOST = "uczen." + "edu" + "vulcan.pl"
_LOGIN_URL = f"{_PORTAL_ROOT}/logowanie"
_VERSION = os.environ.get("MOJV_HELPER_VERSION", "dev")
_BROWSER_TIMEOUT = 35
_CACHE_MAX_AGE = timedelta(hours=6)
_DIAGNOSTIC_SCREENSHOT = "/data/mojv_auth_error.png"

_INVALID_AUTH_MARKERS = (
    "nieprawidłowe hasło",
    "nieprawidlowe haslo",
    "błędne hasło",
    "bledne haslo",
    "nieprawidłowe dane logowania",
    "nieprawidlowe dane logowania",
)
_CHALLENGE_MARKERS = (
    "zabezpieczenie przed robotami",
    "captcha",
    "turnstile",
    "robot verification",
)


class BrowserAuthError(Exception):
    """Base browser authentication error."""


class InvalidCredentials(BrowserAuthError):
    """Credentials were rejected."""


class BrowserVerificationFailed(BrowserAuthError):
    """The browser verification did not complete automatically."""


class NoStudents(BrowserAuthError):
    """No usable student context could be discovered."""


@dataclass(slots=True)
class BrowserAccount:
    """One cached browser session. Passwords are intentionally not retained."""

    driver: webdriver.Chrome
    targets: tuple[StudentTarget, ...]
    authenticated_at: datetime

    def is_fresh(self) -> bool:
        return datetime.now() - self.authenticated_at < _CACHE_MAX_AGE


_ACCOUNTS: dict[str, BrowserAccount] = {}
_BROWSER_LOCK = asyncio.Lock()


def _browser_options() -> Options:
    options = Options()
    binary = shutil.which("chromium-browser") or shutil.which("chromium")
    if binary:
        options.binary_location = binary
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--window-size=1366,900")
    options.add_argument("--lang=pl-PL")
    return options


def _new_driver() -> webdriver.Chrome:
    driver_path = shutil.which("chromedriver")
    if not driver_path:
        raise BrowserAuthError("Chromium driver is not installed")
    try:
        driver = webdriver.Chrome(service=Service(driver_path), options=_browser_options())
        driver.set_page_load_timeout(_BROWSER_TIMEOUT)
        driver.set_script_timeout(25)
        return driver
    except WebDriverException as err:
        raise BrowserAuthError(f"Cannot start Chromium: {err.msg}") from err


def _safe_location(driver: webdriver.Chrome) -> str:
    try:
        parsed = urlparse(driver.current_url)
    except WebDriverException:
        return "unknown"
    host = parsed.netloc or "unknown"
    path = parsed.path or "/"
    return f"{host}{path}"


def _log_stage(driver: webdriver.Chrome, stage: str) -> None:
    _LOGGER.info("Auth stage=%s location=%s", stage, _safe_location(driver))


def _save_diagnostic_screenshot(driver: webdriver.Chrome) -> None:
    try:
        driver.execute_script(
            """
            for (const input of document.querySelectorAll('input')) {
                input.value = '';
                input.setAttribute('value', '');
            }
            """
        )
    except WebDriverException:
        pass
    try:
        if driver.save_screenshot(_DIAGNOSTIC_SCREENSHOT):
            _LOGGER.warning(
                "Auth diagnostic screenshot saved locally: %s",
                _DIAGNOSTIC_SCREENSHOT,
            )
    except WebDriverException:
        pass


def _page_lower(driver: webdriver.Chrome) -> str:
    try:
        return driver.page_source.lower()
    except WebDriverException:
        return ""


def _find_input(driver: webdriver.Chrome, candidates: tuple[str, ...]) -> WebElement | None:
    for candidate in candidates:
        for by in (By.ID, By.NAME):
            try:
                element = driver.find_element(by, candidate)
            except WebDriverException:
                continue
            if element.is_displayed() and element.is_enabled():
                return element
    return None


def _wait_for_input(
    driver: webdriver.Chrome,
    candidates: tuple[str, ...],
    timeout: int = 20,
) -> WebElement:
    try:
        return WebDriverWait(driver, timeout).until(
            lambda current: _find_input(current, candidates)
        )
    except TimeoutException as err:
        lower = _page_lower(driver)
        if any(marker in lower for marker in _CHALLENGE_MARKERS):
            raise BrowserVerificationFailed(
                "Browser verification did not complete"
            ) from err
        raise BrowserAuthError("Expected login field was not found") from err


def _diary_links(driver: webdriver.Chrome) -> list[str]:
    result: list[str] = []
    selectors = (
        'a[href*="dziennik"]',
        'a[href*="Dziennik"]',
    )
    for selector in selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
        except WebDriverException:
            continue
        for element in elements:
            href = (element.get_attribute("href") or "").strip()
            if href and href not in result:
                result.append(href)
    return result


def _wait_for_diary_links(driver: webdriver.Chrome) -> list[str]:
    try:
        links = WebDriverWait(driver, _BROWSER_TIMEOUT).until(
            lambda current: _diary_links(current) or False
        )
        return list(links)
    except TimeoutException as err:
        lower = _page_lower(driver)
        if any(marker in lower for marker in _INVALID_AUTH_MARKERS):
            raise InvalidCredentials("Credentials were rejected") from err
        if any(marker in lower for marker in _CHALLENGE_MARKERS):
            raise BrowserVerificationFailed(
                "Browser verification did not complete"
            ) from err
        raise NoStudents("No diary links were found after login") from err


def _wait_for_student_tenant(
    driver: webdriver.Chrome,
    timeout: int = _BROWSER_TIMEOUT,
) -> str:
    """Wait until SSO lands on a student tenant, regardless of final app route."""

    def ready(current: webdriver.Chrome):
        parsed = urlparse(current.current_url)
        parts = [part for part in parsed.path.split("/") if part]
        if parsed.netloc.lower() == _STUDENT_HOST and parts:
            return current.current_url
        return False

    try:
        return str(WebDriverWait(driver, timeout).until(ready))
    except TimeoutException as err:
        lower = _page_lower(driver)
        if any(marker in lower for marker in _CHALLENGE_MARKERS):
            raise BrowserVerificationFailed(
                "Journal browser verification did not complete"
            ) from err
        raise BrowserAuthError("Journal tenant did not open") from err


def _open_diary_link(
    driver: webdriver.Chrome,
    link: str,
    *,
    index: int,
    total: int,
) -> str:
    """Open one diary link and recover when Chrome waits forever for load."""
    load_timed_out = False
    try:
        driver.get(link)
    except TimeoutException:
        load_timed_out = True
        _LOGGER.warning(
            "Auth stage=diary-link-load-timeout index=%d/%d location=%s",
            index,
            total,
            _safe_location(driver),
        )
        try:
            driver.execute_script("window.stop()")
        except WebDriverException:
            pass
    except WebDriverException as err:
        raise BrowserAuthError("Journal link navigation failed") from err

    return _wait_for_student_tenant(
        driver,
        timeout=5 if load_timed_out else _BROWSER_TIMEOUT,
    )


def _city_from_app_url(app_url: str) -> str:
    parsed = urlparse(app_url)
    parts = [part for part in parsed.path.split("/") if part]
    if parsed.netloc.lower() != _STUDENT_HOST or not parts:
        raise BrowserAuthError("Cannot determine journal tenant")
    return parts[0]


def _browser_fetch(driver: webdriver.Chrome, url: str) -> tuple[int, str]:
    script = """
        const url = arguments[0];
        const done = arguments[arguments.length - 1];
        fetch(url, {
            method: 'GET',
            credentials: 'include',
            headers: {'Accept': 'application/json', 'X-Requested-With': 'XMLHttpRequest'}
        }).then(async response => {
            done({status: response.status, text: await response.text()});
        }).catch(error => done({status: 0, text: String(error)}));
    """
    result = driver.execute_async_script(script, url)
    if not isinstance(result, dict):
        raise BrowserAuthError("Browser request returned an invalid result")
    return int(result.get("status") or 0), str(result.get("text") or "")


def _browser_json(driver: webdriver.Chrome, url: str) -> Any:
    status, text = _browser_fetch(driver, url)
    if status in (401, 403):
        raise BrowserAuthError("Browser session expired")
    if status < 200 or status >= 300:
        raise BrowserAuthError(f"Journal API returned HTTP {status}")
    try:
        return json.loads(text)
    except json.JSONDecodeError as err:
        lower = text.lower()
        if any(marker in lower for marker in _CHALLENGE_MARKERS):
            raise BrowserVerificationFailed(
                "Browser verification interrupted API access"
            ) from err
        raise BrowserAuthError("Journal API returned invalid JSON") from err


def _login_browser(username: str, password: str) -> BrowserAccount:
    driver = _new_driver()
    try:
        driver.get(_LOGIN_URL)
        _log_stage(driver, "login-page")

        username_input = _wait_for_input(
            driver,
            (
                "UserName",
                "Alias",
                "username",
                "alias",
                "Login",
                "login",
                "email",
                "Email",
            ),
        )
        username_input.clear()
        username_input.send_keys(username)
        username_input.send_keys(Keys.ENTER)
        time.sleep(1.5)
        _log_stage(driver, "username-submitted")

        password_input = _wait_for_input(
            driver,
            ("Password", "password"),
            timeout=25,
        )
        password_input.clear()
        password_input.send_keys(password)
        password_input.send_keys(Keys.ENTER)
        _log_stage(driver, "password-submitted")

        links = _wait_for_diary_links(driver)
        _LOGGER.info("Auth stage=diary-links count=%d", len(links))
        targets: list[StudentTarget] = []
        seen: set[tuple[str, str, str]] = set()
        link_failures: list[BrowserAuthError] = []

        for index, link in enumerate(links, start=1):
            try:
                app_url = _open_diary_link(
                    driver,
                    link,
                    index=index,
                    total=len(links),
                )
                _log_stage(driver, "student-app")
                city = _city_from_app_url(app_url)
                context_url = f"https://{_STUDENT_HOST}/{city}/api/Context"
                context = _browser_json(driver, context_url)
                discovered = targets_from_context(city, app_url, context)
                _LOGGER.info(
                    "Auth stage=context index=%d/%d students=%d",
                    index,
                    len(links),
                    len(discovered),
                )
                for target in discovered:
                    identity = (target.city, target.student_id, target.name)
                    if identity in seen:
                        continue
                    seen.add(identity)
                    targets.append(target)
            except BrowserAuthError as err:
                link_failures.append(err)
                _LOGGER.warning(
                    "Auth stage=diary-link-failed index=%d/%d reason=%s location=%s",
                    index,
                    len(links),
                    type(err).__name__,
                    _safe_location(driver),
                )
                continue

        if not targets:
            verification_error = next(
                (
                    err
                    for err in link_failures
                    if isinstance(err, BrowserVerificationFailed)
                ),
                None,
            )
            if verification_error is not None:
                raise verification_error
            if link_failures:
                raise BrowserAuthError("All diary links failed") from link_failures[-1]
            raise NoStudents("Authenticated session contains no usable students")

        _LOGGER.info("Browser session ready: students=%d", len(targets))
        return BrowserAccount(
            driver=driver,
            targets=tuple(targets),
            authenticated_at=datetime.now(),
        )
    except Exception as err:
        _save_diagnostic_screenshot(driver)
        try:
            driver.quit()
        except Exception:
            pass
        if isinstance(err, BrowserAuthError):
            raise
        if isinstance(err, WebDriverException):
            raise BrowserAuthError("Browser navigation failed") from err
        raise


def _close_account(account: BrowserAccount) -> None:
    try:
        account.driver.quit()
    except Exception:
        pass


def _date_stamp(value: datetime, *, start: bool) -> str:
    suffix = "00:00:00.000Z" if start else "23:59:59.999Z"
    return f"{value:%Y-%m-%d}T{suffix}"


def _module_error(error: BrowserAuthError) -> str:
    """Return a secret-free per-module diagnostic value."""
    return type(error).__name__


def _snapshot_browser(account: BrowserAccount) -> dict[str, Any]:
    now = datetime.now()
    date_from = now - timedelta(days=now.weekday() + 7)
    date_to = now + timedelta(days=21)
    schoolwork_from = now.replace(day=1) - timedelta(days=1)
    schoolwork_to = now + timedelta(days=61)
    students: list[dict[str, Any]] = []

    for target in account.targets:
        errors: dict[str, str] = {}
        timetable: Any = None
        attendance: Any = None
        classification_periods: Any = None
        grades_by_period: dict[str, Any] = {}
        schoolwork: Any = None

        try:
            if account.driver.current_url != target.app_url:
                _open_diary_link(
                    account.driver,
                    target.app_url,
                    index=1,
                    total=1,
                )
        except BrowserAuthError as err:
            errors["navigation"] = _module_error(err)

        try:
            plan_params = urlencode(
                {
                    "key": target.session_key,
                    "dataOd": _date_stamp(date_from, start=True),
                    "dataDo": _date_stamp(date_to, start=False),
                    "zakresDanych": "2",
                }
            )
            timetable = _browser_json(
                account.driver,
                f"https://{_STUDENT_HOST}/{target.city}/api/PlanZajec?{plan_params}",
            )
        except BrowserAuthError as err:
            errors["timetable"] = _module_error(err)

        try:
            attendance_params = urlencode({"key": target.session_key})
            attendance = _browser_json(
                account.driver,
                f"https://{_STUDENT_HOST}/{target.city}/api/Frekwencja?{attendance_params}",
            )
        except BrowserAuthError as err:
            errors["attendance"] = _module_error(err)

        try:
            schoolwork_params = urlencode(
                {
                    "key": target.session_key,
                    "dataOd": _date_stamp(schoolwork_from, start=True),
                    "dataDo": _date_stamp(schoolwork_to, start=False),
                }
            )
            schoolwork = _browser_json(
                account.driver,
                f"https://{_STUDENT_HOST}/{target.city}/api/SprawdzianyZadaniaDomowe?{schoolwork_params}",
            )
        except BrowserAuthError as err:
            errors["schoolwork"] = _module_error(err)

        if target.journal_id:
            try:
                periods_params = urlencode(
                    {
                        "key": target.session_key,
                        "idDziennik": target.journal_id,
                    }
                )
                classification_periods = _browser_json(
                    account.driver,
                    f"https://{_STUDENT_HOST}/{target.city}/api/OkresyKlasyfikacyjne?{periods_params}",
                )
            except BrowserAuthError as err:
                errors["classification_periods"] = _module_error(err)

        if isinstance(classification_periods, list):
            for period in classification_periods:
                if not isinstance(period, dict) or period.get("id") is None:
                    continue
                period_id = str(period["id"])
                try:
                    grades_params = urlencode(
                        {
                            "key": target.session_key,
                            "idOkresKlasyfikacyjny": period_id,
                        }
                    )
                    grades_by_period[period_id] = _browser_json(
                        account.driver,
                        f"https://{_STUDENT_HOST}/{target.city}/api/Oceny?{grades_params}",
                    )
                except BrowserAuthError as err:
                    errors[f"grades:{period_id}"] = _module_error(err)

        students.append(
            public_snapshot_row(
                target,
                timetable=timetable,
                attendance=attendance,
                classification_periods=classification_periods,
                grades_by_period=grades_by_period,
                schoolwork=schoolwork,
                errors=errors,
            )
        )

    return {
        "students": students,
        "fetched_at": now.isoformat(timespec="seconds"),
    }


async def _get_account(
    username: str,
    password: str,
    *,
    force: bool = False,
) -> BrowserAccount:
    key = credential_cache_key(username, password)
    async with _BROWSER_LOCK:
        cached = _ACCOUNTS.get(key)
        if cached is not None and not force and cached.is_fresh():
            return cached
        if cached is not None:
            _close_account(cached)
            _ACCOUNTS.pop(key, None)
        account = await asyncio.to_thread(_login_browser, username, password)
        _ACCOUNTS[key] = account
        return account


async def _request_credentials(request: web.Request) -> tuple[str, str]:
    try:
        payload = await request.json()
    except (json.JSONDecodeError, ValueError):
        raise web.HTTPBadRequest(
            text='{"error":"invalid_json"}',
            content_type="application/json",
        )
    if not isinstance(payload, dict):
        raise web.HTTPBadRequest(
            text='{"error":"invalid_json"}',
            content_type="application/json",
        )
    username = str(payload.get("username") or "").strip()
    password = str(payload.get("password") or "")
    if not username or not password:
        raise web.HTTPBadRequest(
            text='{"error":"missing_credentials"}',
            content_type="application/json",
        )
    return username, password


def _error_response(err: Exception) -> web.Response:
    if isinstance(err, InvalidCredentials):
        status, code = 401, "invalid_auth"
    elif isinstance(err, BrowserVerificationFailed):
        status, code = 503, "browser_verification_failed"
    elif isinstance(err, NoStudents):
        status, code = 422, "no_students"
    else:
        status, code = 503, "browser_error"
    _LOGGER.warning("Browser helper request failed: %s", code)
    return web.json_response({"error": code}, status=status)


async def health(_: web.Request) -> web.Response:
    return web.json_response({"status": "ok", "version": _VERSION})


async def index(_: web.Request) -> web.Response:
    return web.Response(
        text=(
            "mojV Auth Helper is running. This local service only handles "
            "browser-backed authentication for the mojV Home Assistant integration."
        )
    )


async def account(request: web.Request) -> web.Response:
    username, password = await _request_credentials(request)
    try:
        browser_account = await _get_account(username, password)
    except BrowserAuthError as err:
        return _error_response(err)
    return web.json_response(
        {"students": [target.public_dict() for target in browser_account.targets]}
    )


async def snapshot(request: web.Request) -> web.Response:
    username, password = await _request_credentials(request)
    try:
        browser_account = await _get_account(username, password)
        async with _BROWSER_LOCK:
            result = await asyncio.to_thread(_snapshot_browser, browser_account)
        if result["students"] and all(
            row.get("errors")
            and row.get("timetable") is None
            and row.get("attendance") is None
            for row in result["students"]
        ):
            browser_account = await _get_account(username, password, force=True)
            async with _BROWSER_LOCK:
                result = await asyncio.to_thread(_snapshot_browser, browser_account)
        return web.json_response(result)
    except BrowserAuthError as err:
        return _error_response(err)


async def cleanup(_: web.Application) -> None:
    async with _BROWSER_LOCK:
        for browser_account in tuple(_ACCOUNTS.values()):
            await asyncio.to_thread(_close_account, browser_account)
        _ACCOUNTS.clear()


def create_app() -> web.Application:
    app = web.Application(client_max_size=64 * 1024)
    app.router.add_get("/", index)
    app.router.add_get("/health", health)
    app.router.add_post("/v1/account", account)
    app.router.add_post("/v1/snapshot", snapshot)
    app.on_cleanup.append(cleanup)
    return app


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    web.run_app(create_app(), host="0.0.0.0", port=8099, access_log=None)

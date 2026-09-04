"""Extended LIVE snapshot layer for mojV Auth Helper 0.1.8."""
from __future__ import annotations

from datetime import datetime, timedelta
import hashlib
import logging
from typing import Any
from urllib.parse import urlencode, urlparse

import server as base

_MESSAGES_HOST = "wiadomosci.eduvulcan.pl"


def _json_url(host: str, path: str, params: dict[str, Any]) -> str:
    query = urlencode(params)
    return f"https://{host}{path}?{query}" if query else f"https://{host}{path}"


def _records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("wiadomosci", "data", "result"):
            rows = payload.get(key)
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)]
    return []


def _public_message_id(value: str) -> str:
    """Return a stable public identifier without exposing message routing keys."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def _sanitize_detail(value: Any) -> Any:
    """Recursively remove known routing/auth fields from message payloads."""
    forbidden = {
        "apiglobalkey",
        "globalkeyskrzynka",
        "mailbox_key",
        "session_key",
        "journal_id",
        "cookie",
        "cookies",
        "token",
    }
    if isinstance(value, dict):
        return {
            str(key): _sanitize_detail(child)
            for key, child in value.items()
            if str(key).lower() not in forbidden
        }
    if isinstance(value, list):
        return [_sanitize_detail(item) for item in value]
    return value


def _fetch_module(
    driver: Any,
    target: Any,
    endpoint: str,
    params: dict[str, Any],
    errors: dict[str, str],
    error_key: str,
) -> Any:
    try:
        return base._browser_json(
            driver,
            _json_url(
                base._STUDENT_HOST,
                f"/{target.city}/api/{endpoint}",
                params,
            ),
        )
    except base.BrowserAuthError as err:
        errors[error_key] = base._module_error(err)
        return None


def _open_messages_app(driver: Any, city: str) -> None:
    app_url = f"https://{_MESSAGES_HOST}/{city}/App"
    try:
        driver.get(app_url)
    except base.TimeoutException:
        try:
            driver.execute_script("window.stop()")
        except base.WebDriverException:
            pass
    except base.WebDriverException as err:
        raise base.BrowserAuthError("Message tenant navigation failed") from err

    def ready(current: Any):
        try:
            parsed = urlparse(current.current_url)
        except base.WebDriverException:
            return False
        return parsed.netloc.lower() == _MESSAGES_HOST and parsed.path.startswith(f"/{city}/")

    try:
        base.WebDriverWait(driver, 12).until(ready)
    except base.TimeoutException as err:
        raise base.BrowserAuthError("Message tenant did not open") from err


def _fetch_messages(
    driver: Any,
    target: Any,
    errors: dict[str, str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not target.mailbox_key:
        return [], {}
    try:
        _open_messages_app(driver, target.city)
        inbox_payload = base._browser_json(
            driver,
            _json_url(
                _MESSAGES_HOST,
                f"/{target.city}/api/OdebraneSkrzynka",
                {
                    "globalKeySkrzynka": target.mailbox_key,
                    "idLastWiadomosc": 0,
                    "pageSize": 50,
                },
            ),
        )
        inbox: list[dict[str, Any]] = []
        details: dict[str, Any] = {}
        for raw in _records(inbox_payload):
            routing_key = str(raw.get("apiGlobalKey") or "").strip()
            public_id = _public_message_id(routing_key) if routing_key else str(raw.get("id") or "")
            row = {
                str(key): _sanitize_detail(value)
                for key, value in raw.items()
                if str(key).lower() not in {"apiglobalkey", "globalkeyskrzynka"}
            }
            if public_id:
                row["id"] = public_id
            inbox.append(row)
            if not routing_key or not public_id:
                continue
            try:
                detail = base._browser_json(
                    driver,
                    _json_url(
                        _MESSAGES_HOST,
                        f"/{target.city}/api/WiadomoscSzczegoly",
                        {"apiGlobalKey": routing_key},
                    ),
                )
                details[public_id] = _sanitize_detail(detail)
            except base.BrowserAuthError as err:
                errors[f"message_detail:{public_id}"] = base._module_error(err)
        return inbox, details
    except base.BrowserAuthError as err:
        errors["messages"] = base._module_error(err)
        return [], {}


def _snapshot_browser(account: base.BrowserAccount) -> dict[str, Any]:
    now = datetime.now()
    date_from = now - timedelta(days=now.weekday() + 7)
    date_to = now + timedelta(days=21)
    schoolwork_from = now.replace(day=1) - timedelta(days=1)
    schoolwork_to = now + timedelta(days=61)
    students: list[dict[str, Any]] = []

    for target in account.targets:
        errors: dict[str, str] = {}
        try:
            if account.driver.current_url != target.app_url:
                base._open_diary_link(account.driver, target.app_url, index=1, total=1)
        except base.BrowserAuthError as err:
            errors["navigation"] = base._module_error(err)

        common = {"key": target.session_key}
        timetable = _fetch_module(
            account.driver,
            target,
            "PlanZajec",
            {
                **common,
                "dataOd": base._date_stamp(date_from, start=True),
                "dataDo": base._date_stamp(date_to, start=False),
                "zakresDanych": "2",
            },
            errors,
            "timetable",
        )
        attendance = _fetch_module(account.driver, target, "Frekwencja", common, errors, "attendance")
        attendance_subjects = _fetch_module(account.driver, target, "Przedmioty", common, errors, "attendance_subjects")
        attendance_summary = _fetch_module(
            account.driver,
            target,
            "FrekwencjaStatystyki",
            {**common, "idPrzedmiot": -1},
            errors,
            "attendance_summary",
        )
        attendance_by_subject: dict[str, Any] = {}
        if isinstance(attendance_subjects, list):
            for row in attendance_subjects:
                if not isinstance(row, dict) or row.get("id") is None or str(row.get("id")) == "-1":
                    continue
                subject_id = str(row["id"])
                result = _fetch_module(
                    account.driver,
                    target,
                    "FrekwencjaStatystyki",
                    {**common, "idPrzedmiot": row["id"]},
                    errors,
                    f"attendance_stats:{subject_id}",
                )
                if result is not None:
                    attendance_by_subject[subject_id] = result

        remarks = _fetch_module(account.driver, target, "Uwagi", common, errors, "remarks")
        achievements = _fetch_module(account.driver, target, "Osiagniecia", common, errors, "achievements")
        meetings = _fetch_module(account.driver, target, "Zebrania", common, errors, "meetings")
        schoolwork = _fetch_module(
            account.driver,
            target,
            "SprawdzianyZadaniaDomowe",
            {
                **common,
                "dataOd": base._date_stamp(schoolwork_from, start=True),
                "dataDo": base._date_stamp(schoolwork_to, start=False),
            },
            errors,
            "schoolwork",
        )

        classification_periods: Any = None
        grades_by_period: dict[str, Any] = {}
        if target.journal_id:
            classification_periods = _fetch_module(
                account.driver,
                target,
                "OkresyKlasyfikacyjne",
                {**common, "idDziennik": target.journal_id},
                errors,
                "classification_periods",
            )
        if isinstance(classification_periods, list):
            for period in classification_periods:
                if not isinstance(period, dict) or period.get("id") is None:
                    continue
                period_id = str(period["id"])
                result = _fetch_module(
                    account.driver,
                    target,
                    "Oceny",
                    {**common, "idOkresKlasyfikacyjny": period_id},
                    errors,
                    f"grades:{period_id}",
                )
                if result is not None:
                    grades_by_period[period_id] = result

        messages, message_details = _fetch_messages(account.driver, target, errors)
        try:
            base._open_diary_link(account.driver, target.app_url, index=1, total=1)
        except base.BrowserAuthError as err:
            errors.setdefault("navigation_restore", base._module_error(err))

        students.append(
            base.public_snapshot_row(
                target,
                timetable=timetable,
                attendance=attendance,
                attendance_subjects=attendance_subjects,
                attendance_summary=attendance_summary,
                attendance_by_subject=attendance_by_subject,
                classification_periods=classification_periods,
                grades_by_period=grades_by_period,
                remarks=remarks,
                schoolwork=schoolwork,
                messages=messages,
                message_details=message_details,
                achievements=achievements,
                meetings=meetings,
                errors=errors,
            )
        )

    return {"students": students, "fetched_at": now.isoformat(timespec="seconds")}


base._snapshot_browser = _snapshot_browser


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    base.web.run_app(base.create_app(), host="0.0.0.0", port=8099, access_log=None)

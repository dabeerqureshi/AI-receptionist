from __future__ import annotations

import json
import os
from types import SimpleNamespace
from urllib import error, request


class APIError(Exception):
    pass


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")


def _to_namespace(value):
    if isinstance(value, dict):
        return SimpleNamespace(**{key: _to_namespace(item) for key, item in value.items()})
    if isinstance(value, list):
        return [_to_namespace(item) for item in value]
    return value


def api_request(
    method: str,
    path: str,
    payload: dict | None = None,
    admin_token: str | None = None,
    api_key: str | None = None,
):
    url = f"{API_BASE_URL}{path}"
    body = None
    headers = {"Content-Type": "application/json"}

    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
    if admin_token:
        headers["Authorization"] = f"Bearer {admin_token}"
    if api_key:
        headers["X-API-Key"] = api_key

    req = request.Request(url, data=body, headers=headers, method=method.upper())
    try:
        with request.urlopen(req, timeout=20) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except error.HTTPError as exc:
        details = exc.read().decode("utf-8")
        try:
            parsed = json.loads(details)
            message = parsed.get("detail", details)
        except json.JSONDecodeError:
            message = details or str(exc)
        raise APIError(message) from exc
    except error.URLError as exc:
        raise APIError(f"Could not reach API at {API_BASE_URL}. Is the FastAPI server running?") from exc


def admin_login(username: str, password: str) -> str:
    response = api_request(
        "POST",
        "/admin/auth/login",
        payload={"username": username, "password": password},
    )
    return response["token"]


def admin_get_summary(token: str) -> dict:
    return api_request("GET", "/admin/summary", admin_token=token)


def admin_get_clinics(token: str):
    response = api_request("GET", "/admin/clinics", admin_token=token)
    return _to_namespace(response["clinics"])


def admin_create_clinic(token: str, clinic_name: str, timezone: str, appointment_duration: int) -> dict:
    return api_request(
        "POST",
        "/admin/clinics",
        payload={
            "clinic_name": clinic_name,
            "timezone": timezone,
            "appointment_duration": appointment_duration,
        },
        admin_token=token,
    )


def admin_rotate_api_key(token: str, clinic_id: str) -> str:
    response = api_request(
        "POST",
        f"/admin/clinics/{clinic_id}/rotate-api-key",
        admin_token=token,
    )
    return response["api_key"]


def admin_update_working_hours(token: str, clinic_id: str, working_hours: list[tuple[int, object, object]]) -> None:
    payload = {
        "working_hours": [
            {
                "day_of_week": day_num,
                "start_time": start_time.strftime("%H:%M"),
                "end_time": end_time.strftime("%H:%M"),
            }
            for day_num, start_time, end_time in working_hours
        ]
    }
    api_request(
        "PUT",
        f"/admin/clinics/{clinic_id}/working-hours",
        payload=payload,
        admin_token=token,
    )


def admin_delete_clinic(token: str, clinic_id: str) -> None:
    api_request("DELETE", f"/admin/clinics/{clinic_id}", admin_token=token)


def admin_get_appointments(token: str):
    response = api_request("GET", "/admin/appointments", admin_token=token)
    return _to_namespace(response["appointments"])


def admin_delete_all_appointments(token: str) -> None:
    api_request("DELETE", "/admin/appointments", admin_token=token)


def admin_get_system_health(token: str) -> dict:
    return api_request("GET", "/admin/system/health", admin_token=token)


def admin_clear_all_data(token: str) -> None:
    api_request("DELETE", "/admin/system/data", admin_token=token)


def tenant_verify_credentials(clinic_id: str, api_key: str):
    response = api_request(
        "POST",
        "/tenant/auth/verify",
        payload={"clinic_id": clinic_id, "api_key": api_key},
    )
    return response["clinic_id"], response["clinic_name"]


def tenant_get_clinic(api_key: str):
    return _to_namespace(api_request("GET", "/tenant/clinic", api_key=api_key))


def tenant_get_settings(api_key: str):
    response = api_request("GET", "/clinic/settings", api_key=api_key)
    return _to_namespace(response)


def tenant_get_working_hours(api_key: str):
    settings = tenant_get_settings(api_key)
    return settings.working_hours


def tenant_get_appointments(api_key: str):
    response = api_request("GET", "/tenant/appointments", api_key=api_key)
    return _to_namespace(response["appointments"])


def tenant_get_appointment(api_key: str, appointment_id: int):
    response = api_request("GET", f"/tenant/appointments/{appointment_id}", api_key=api_key)
    return _to_namespace(response)


def tenant_create_appointment(
    api_key: str,
    name: str,
    phone: str,
    appointment_date: str,
    appointment_time: str,
    reason: str,
) -> None:
    api_request(
        "POST",
        "/tenant/appointments",
        payload={
            "name": name,
            "phone": phone,
            "date": appointment_date,
            "time": appointment_time,
            "reason": reason,
        },
        api_key=api_key,
    )


def tenant_update_appointment(
    api_key: str,
    appointment_id: int,
    name: str,
    phone: str,
    appointment_date: str,
    appointment_time: str,
    reason: str,
) -> None:
    api_request(
        "PUT",
        f"/tenant/appointments/{appointment_id}",
        payload={
            "name": name,
            "phone": phone,
            "date": appointment_date,
            "time": appointment_time,
            "reason": reason,
        },
        api_key=api_key,
    )


def tenant_delete_appointment(api_key: str, appointment_id: int) -> None:
    api_request("DELETE", f"/tenant/appointments/{appointment_id}", api_key=api_key)


def tenant_update_working_hours(api_key: str, working_hours: list[tuple[int, object, object]]) -> None:
    payload = {
        "working_hours": [
            {
                "day_of_week": day_num,
                "start_time": start_time.strftime("%H:%M"),
                "end_time": end_time.strftime("%H:%M"),
            }
            for day_num, start_time, end_time in working_hours
        ]
    }
    api_request("PUT", "/tenant/working-hours", payload=payload, api_key=api_key)


def tenant_update_settings(api_key: str, appointment_duration: int) -> None:
    api_request(
        "PUT",
        "/tenant/settings",
        payload={"appointment_duration": appointment_duration},
        api_key=api_key,
    )

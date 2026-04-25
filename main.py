import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from database import Clinic, ClinicSettings, SessionLocal, WorkingHours
from dashboard_backend import (
    check_database_connection,
    clear_all_data,
    create_clinic,
    create_tenant_appointment,
    delete_all_appointments,
    delete_clinic,
    delete_tenant_appointment,
    get_admin_dashboard_summary,
    get_all_clinics,
    get_all_appointments,
    get_clinic_by_id,
    get_clinic_settings,
    get_clinic_working_hours,
    get_tenant_appointment,
    get_tenant_appointments,
    rotate_clinic_api_key,
    save_clinic_working_hours,
    update_tenant_appointment,
    update_tenant_appointment_duration,
    update_tenant_working_hours,
    verify_tenant_credentials,
)
from services import book_appointment, get_available_slots, get_clinic_by_api_key

load_dotenv()

app = FastAPI(title="AI Receptionist API", version="3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "").strip()
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH", "").strip()
ADMIN_SESSION_TIMEOUT_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES", "30"))
admin_sessions: dict[str, datetime] = {}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def validate_admin_credentials(username: str, password: str) -> bool:
    username_ok = hmac.compare_digest(username, ADMIN_USERNAME)
    password_ok = hmac.compare_digest(hash_password(password), ADMIN_PASSWORD_HASH)
    return username_ok and password_ok


def create_admin_session() -> str:
    token = secrets.token_hex(32)
    admin_sessions[token] = datetime.utcnow() + timedelta(
        minutes=ADMIN_SESSION_TIMEOUT_MINUTES
    )
    return token


def cleanup_admin_sessions() -> None:
    now = datetime.utcnow()
    expired = [
        token for token, expires_at in admin_sessions.items() if expires_at <= now
    ]
    for token in expired:
        admin_sessions.pop(token, None)


def serialize_working_hour(working_hour: WorkingHours) -> dict:
    return {
        "day_of_week": working_hour.day_of_week,
        "start_time": working_hour.start_time.strftime("%H:%M"),
        "end_time": working_hour.end_time.strftime("%H:%M"),
    }


def serialize_clinic_settings(settings: ClinicSettings | None) -> dict:
    return {
        "timezone": settings.timezone if settings else "UTC",
        "appointment_duration": settings.appointment_duration if settings else 30,
    }


def serialize_clinic(db: Session, clinic: Clinic) -> dict:
    settings = get_clinic_settings(db, clinic.id)
    working_hours = get_clinic_working_hours(db, clinic.id)
    appointment_count = len(get_tenant_appointments(db, clinic.id))
    return {
        "id": clinic.id,
        "name": clinic.name,
        "api_key": clinic.api_key,
        "settings": serialize_clinic_settings(settings),
        "working_hours": [serialize_working_hour(item) for item in working_hours],
        "appointment_count": appointment_count,
    }


def serialize_appointment(appointment) -> dict:
    return {
        "id": appointment.id,
        "tenant_id": appointment.tenant_id,
        "name": appointment.name,
        "phone": appointment.phone,
        "date": appointment.date,
        "time": appointment.time,
        "reason": appointment.reason,
    }


async def get_tenant(x_api_key: str = Header(...), db: Session = Depends(get_db)):
    clinic = get_clinic_by_api_key(db, x_api_key)
    if not clinic:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return clinic


async def get_admin(
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    cleanup_admin_sessions()
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing admin token")

    token = authorization.removeprefix("Bearer ").strip()
    expires_at = admin_sessions.get(token)
    if expires_at is None or expires_at <= datetime.utcnow():
        admin_sessions.pop(token, None)
        raise HTTPException(status_code=401, detail="Admin session expired")

    admin_sessions[token] = datetime.utcnow() + timedelta(
        minutes=ADMIN_SESSION_TIMEOUT_MINUTES
    )
    return {"token": token, "db_ok": check_database_connection(db)}


class AvailabilityRequest(BaseModel):
    date: str

    @field_validator("date")
    def validate_date_format(cls, value):
        try:
            datetime.strptime(value, "%Y-%m-%d")
            return value
        except ValueError as exc:
            raise ValueError("Invalid date format. Use YYYY-MM-DD") from exc


class BookingRequest(BaseModel):
    name: str
    phone: str
    date: str
    time: str
    reason: str

    @field_validator("date")
    def validate_date_format(cls, value):
        try:
            datetime.strptime(value, "%Y-%m-%d")
            return value
        except ValueError as exc:
            raise ValueError("Invalid date format. Use YYYY-MM-DD") from exc

    @field_validator("time")
    def validate_time_format(cls, value):
        try:
            datetime.strptime(value, "%H:%M")
            return value
        except ValueError as exc:
            raise ValueError("Invalid time format. Use HH:MM") from exc


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class TenantAuthRequest(BaseModel):
    clinic_id: str
    api_key: str


class ClinicCreateRequest(BaseModel):
    clinic_name: str
    timezone: str
    appointment_duration: int


class TimeRangePayload(BaseModel):
    day_of_week: int
    start_time: str
    end_time: str

    @field_validator("start_time", "end_time")
    def validate_time(cls, value):
        try:
            datetime.strptime(value, "%H:%M")
            return value
        except ValueError as exc:
            raise ValueError("Invalid time format. Use HH:MM") from exc


class WorkingHoursUpdateRequest(BaseModel):
    working_hours: list[TimeRangePayload]


class TenantAppointmentRequest(BaseModel):
    name: str
    phone: str
    date: str
    time: str
    reason: str

    @field_validator("date")
    def validate_date(cls, value):
        try:
            datetime.strptime(value, "%Y-%m-%d")
            return value
        except ValueError as exc:
            raise ValueError("Invalid date format. Use YYYY-MM-DD") from exc

    @field_validator("time")
    def validate_time(cls, value):
        try:
            datetime.strptime(value, "%H:%M")
            return value
        except ValueError as exc:
            raise ValueError("Invalid time format. Use HH:MM") from exc


class TenantSettingsUpdateRequest(BaseModel):
    appointment_duration: int


def parse_working_hours(
    payload: WorkingHoursUpdateRequest,
) -> list[tuple[int, datetime.time, datetime.time]]:
    parsed = []
    for item in payload.working_hours:
        start_time = datetime.strptime(item.start_time, "%H:%M").time()
        end_time = datetime.strptime(item.end_time, "%H:%M").time()
        if start_time >= end_time:
            raise HTTPException(
                status_code=400,
                detail=f"Day {item.day_of_week}: close time must be after open time",
            )
        parsed.append((item.day_of_week, start_time, end_time))
    return parsed


@app.get("/")
def root():
    return {"message": "AI Receptionist Multi-Tenant API", "status": "online"}


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    return {
        "status": "healthy" if check_database_connection(db) else "degraded",
        "version": "3.0",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.post("/admin/auth/login")
def admin_login(request: AdminLoginRequest):
    if not ADMIN_USERNAME or not ADMIN_PASSWORD_HASH:
        raise HTTPException(
            status_code=500, detail="Admin credentials are not configured"
        )
    if not validate_admin_credentials(request.username, request.password):
        raise HTTPException(status_code=401, detail="Invalid admin credentials")

    token = create_admin_session()
    return {
        "token": token,
        "expires_in_minutes": ADMIN_SESSION_TIMEOUT_MINUTES,
    }


@app.post("/tenant/auth/verify")
def tenant_auth_verify(request: TenantAuthRequest, db: Session = Depends(get_db)):
    is_valid, clinic_name = verify_tenant_credentials(
        db, request.clinic_id, request.api_key
    )
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid clinic ID or API key")
    return {
        "clinic_id": request.clinic_id,
        "clinic_name": clinic_name,
    }


@app.get("/admin/summary")
def admin_summary(_: dict = Depends(get_admin), db: Session = Depends(get_db)):
    return get_admin_dashboard_summary(db)


@app.get("/admin/clinics")
def admin_clinics(_: dict = Depends(get_admin), db: Session = Depends(get_db)):
    clinics = get_all_clinics(db)
    return {"clinics": [serialize_clinic(db, clinic) for clinic in clinics]}


@app.post("/admin/clinics")
def admin_create_clinic(
    request: ClinicCreateRequest,
    _: dict = Depends(get_admin),
    db: Session = Depends(get_db),
):
    clinic_id, api_key = create_clinic(
        db,
        request.clinic_name.strip(),
        request.timezone,
        request.appointment_duration,
    )
    return {
        "clinic_id": clinic_id,
        "api_key": api_key,
    }


@app.post("/admin/clinics/{clinic_id}/rotate-api-key")
def admin_rotate_clinic_api_key(
    clinic_id: str,
    _: dict = Depends(get_admin),
    db: Session = Depends(get_db),
):
    try:
        new_key = rotate_clinic_api_key(db, clinic_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"api_key": new_key}


@app.put("/admin/clinics/{clinic_id}/working-hours")
def admin_update_clinic_working_hours(
    clinic_id: str,
    request: WorkingHoursUpdateRequest,
    _: dict = Depends(get_admin),
    db: Session = Depends(get_db),
):
    save_clinic_working_hours(db, clinic_id, parse_working_hours(request))
    return {"success": True}


@app.delete("/admin/clinics/{clinic_id}")
def admin_delete_clinic(
    clinic_id: str,
    _: dict = Depends(get_admin),
    db: Session = Depends(get_db),
):
    delete_clinic(db, clinic_id)
    return {"success": True}


@app.get("/admin/appointments")
def admin_appointments(_: dict = Depends(get_admin), db: Session = Depends(get_db)):
    appointments = [serialize_appointment(item) for item in get_all_appointments(db)]
    return {"appointments": appointments}


@app.delete("/admin/appointments")
def admin_delete_appointments(
    _: dict = Depends(get_admin), db: Session = Depends(get_db)
):
    delete_all_appointments(db)
    return {"success": True}


@app.get("/admin/system/health")
def admin_system_health(_: dict = Depends(get_admin), db: Session = Depends(get_db)):
    return {
        "database_connected": check_database_connection(db),
        "session_timeout_minutes": ADMIN_SESSION_TIMEOUT_MINUTES,
    }


@app.delete("/admin/system/data")
def admin_clear_system_data(
    _: dict = Depends(get_admin), db: Session = Depends(get_db)
):
    clear_all_data(db)
    return {"success": True}


@app.post("/check-availability")
def check_date_availability(
    request: AvailabilityRequest,
    clinic: Clinic = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    slots = get_available_slots(db, clinic.id, request.date)
    return {
        "tenant_id": clinic.id,
        "clinic_name": clinic.name,
        "date": request.date,
        "available_slots": slots,
    }


@app.post("/book-appointment")
def create_booking(
    request: BookingRequest,
    clinic: Clinic = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    result = book_appointment(
        db=db,
        tenant_id=clinic.id,
        name=request.name,
        phone=request.phone,
        date=request.date,
        time=request.time,
        reason=request.reason,
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@app.get("/clinic/settings")
def clinic_settings(
    clinic: Clinic = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    settings = get_clinic_settings(db, clinic.id)
    working_hours = get_clinic_working_hours(db, clinic.id)
    return {
        "clinic_id": clinic.id,
        "name": clinic.name,
        "timezone": settings.timezone if settings else "UTC",
        "appointment_duration": settings.appointment_duration if settings else 30,
        "working_hours": [serialize_working_hour(item) for item in working_hours],
    }


@app.get("/tenant/clinic")
def tenant_clinic(clinic: Clinic = Depends(get_tenant), db: Session = Depends(get_db)):
    settings = get_clinic_settings(db, clinic.id)
    return {
        "id": clinic.id,
        "name": clinic.name,
        "timezone": settings.timezone if settings else "UTC",
    }


@app.get("/tenant/appointments")
def tenant_appointments(
    clinic: Clinic = Depends(get_tenant), db: Session = Depends(get_db)
):
    appointments = get_tenant_appointments(db, clinic.id)
    return {"appointments": [serialize_appointment(item) for item in appointments]}


@app.post("/tenant/appointments")
def tenant_create_appointment_endpoint(
    request: TenantAppointmentRequest,
    clinic: Clinic = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    create_tenant_appointment(
        db,
        clinic.id,
        request.name,
        request.phone,
        request.date,
        request.time,
        request.reason,
    )
    return {"success": True}


@app.put("/tenant/appointments/{appointment_id}")
def tenant_update_appointment_endpoint(
    appointment_id: int,
    request: TenantAppointmentRequest,
    clinic: Clinic = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    try:
        appointment = update_tenant_appointment(
            db,
            clinic.id,
            appointment_id,
            request.name,
            request.phone,
            request.date,
            request.time,
            request.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True, "appointment": serialize_appointment(appointment)}


@app.delete("/tenant/appointments/{appointment_id}")
def tenant_delete_appointment_endpoint(
    appointment_id: int,
    clinic: Clinic = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    try:
        delete_tenant_appointment(db, clinic.id, appointment_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True}


@app.get("/tenant/appointments/{appointment_id}")
def tenant_get_appointment_endpoint(
    appointment_id: int,
    clinic: Clinic = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    appointment = get_tenant_appointment(db, clinic.id, appointment_id)
    if appointment is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return serialize_appointment(appointment)


@app.put("/tenant/working-hours")
def tenant_update_working_hours_endpoint(
    request: WorkingHoursUpdateRequest,
    clinic: Clinic = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    update_tenant_working_hours(db, clinic.id, parse_working_hours(request))
    return {"success": True}


@app.put("/tenant/settings")
def tenant_update_settings_endpoint(
    request: TenantSettingsUpdateRequest,
    clinic: Clinic = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    try:
        update_tenant_appointment_duration(db, clinic.id, request.appointment_duration)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

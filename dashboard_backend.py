from __future__ import annotations

import hmac
import secrets
from datetime import time

import pandas as pd
from sqlalchemy.orm import Session

from database import Appointment, Clinic, ClinicSettings, SessionLocal, WorkingHours


def get_db_session() -> Session:
    return SessionLocal()


def generate_api_key() -> str:
    return secrets.token_hex(16)


def verify_tenant_credentials(db: Session, clinic_id: str, api_key: str) -> tuple[bool, str | None]:
    clinic = db.query(Clinic).filter(Clinic.id == clinic_id).first()
    if clinic is None:
        hmac.compare_digest("dummy", "dummy2")
        return False, None
    if hmac.compare_digest(clinic.api_key, api_key):
        return True, clinic.name
    return False, None


def get_all_clinics(db: Session):
    return db.query(Clinic).all()


def get_clinic_by_id(db: Session, clinic_id: str):
    return db.query(Clinic).filter(Clinic.id == clinic_id).first()


def get_clinic_settings(db: Session, clinic_id: str):
    return db.query(ClinicSettings).filter(ClinicSettings.tenant_id == clinic_id).first()


def get_clinic_working_hours(db: Session, clinic_id: str):
    return db.query(WorkingHours).filter(WorkingHours.tenant_id == clinic_id).all()


def get_all_appointments(db: Session):
    return db.query(Appointment).all()


def get_tenant_appointments(db: Session, clinic_id: str):
    return (
        db.query(Appointment)
        .filter(Appointment.tenant_id == clinic_id)
        .order_by(Appointment.date, Appointment.time)
        .all()
    )


def get_tenant_appointment(db: Session, clinic_id: str, appointment_id: int):
    return (
        db.query(Appointment)
        .filter(Appointment.id == appointment_id, Appointment.tenant_id == clinic_id)
        .first()
    )


def get_appointments_df(db: Session) -> pd.DataFrame:
    appointments = get_all_appointments(db)
    if not appointments:
        return pd.DataFrame()

    clinic_map = {clinic.id: clinic.name for clinic in get_all_clinics(db)}
    rows = []
    for appointment in appointments:
        rows.append(
            {
                "id": appointment.id,
                "clinic_id": appointment.tenant_id,
                "Clinic": clinic_map.get(appointment.tenant_id, "Unknown"),
                "Patient": appointment.name,
                "Phone": appointment.phone,
                "Date": pd.to_datetime(appointment.date),
                "Time": str(appointment.time),
                "Reason": appointment.reason,
            }
        )
    return pd.DataFrame(rows)


def get_admin_dashboard_summary(db: Session) -> dict[str, int]:
    return {
        "total_clinics": db.query(Clinic).count(),
        "total_appointments": db.query(Appointment).count(),
        "total_working_hours": db.query(WorkingHours).count(),
    }


def create_clinic(db: Session, clinic_name: str, timezone: str, appointment_duration: int) -> tuple[str, str]:
    clinic_id = f"clinic_{secrets.token_hex(4)}"
    api_key = generate_api_key()

    db.add(Clinic(id=clinic_id, name=clinic_name, api_key=api_key))
    db.add(
        ClinicSettings(
            tenant_id=clinic_id,
            timezone=timezone,
            appointment_duration=appointment_duration,
        )
    )

    for day in range(5):
        db.add(
            WorkingHours(
                tenant_id=clinic_id,
                day_of_week=day,
                start_time=time(9, 0),
                end_time=time(17, 0),
            )
        )

    db.commit()
    return clinic_id, api_key


def rotate_clinic_api_key(db: Session, clinic_id: str) -> str:
    clinic = get_clinic_by_id(db, clinic_id)
    if clinic is None:
        raise ValueError("Clinic not found")

    new_key = generate_api_key()
    clinic.api_key = new_key
    db.commit()
    return new_key


def delete_clinic(db: Session, clinic_id: str) -> None:
    db.query(WorkingHours).filter(WorkingHours.tenant_id == clinic_id).delete()
    db.query(ClinicSettings).filter(ClinicSettings.tenant_id == clinic_id).delete()
    db.query(Appointment).filter(Appointment.tenant_id == clinic_id).delete()
    db.query(Clinic).filter(Clinic.id == clinic_id).delete()
    db.commit()


def save_clinic_working_hours(db: Session, clinic_id: str, updated_hours: list[tuple[int, time, time]]) -> None:
    db.query(WorkingHours).filter(WorkingHours.tenant_id == clinic_id).delete()
    for day_num, start_time, end_time in updated_hours:
        db.add(
            WorkingHours(
                tenant_id=clinic_id,
                day_of_week=day_num,
                start_time=start_time,
                end_time=end_time,
            )
        )
    db.commit()


def delete_all_appointments(db: Session) -> None:
    db.query(Appointment).delete()
    db.commit()


def clear_all_data(db: Session) -> None:
    db.query(Appointment).delete()
    db.query(WorkingHours).delete()
    db.query(ClinicSettings).delete()
    db.query(Clinic).delete()
    db.commit()


def check_database_connection(db: Session) -> bool:
    try:
        db.query(Clinic).count()
        return True
    except Exception:
        return False


def create_tenant_appointment(
    db: Session,
    clinic_id: str,
    name: str,
    phone: str,
    appointment_date: str,
    appointment_time: str,
    reason: str,
) -> None:
    db.add(
        Appointment(
            tenant_id=clinic_id,
            name=name,
            phone=phone,
            date=appointment_date,
            time=appointment_time,
            reason=reason,
        )
    )
    db.commit()


def update_tenant_appointment(
    db: Session,
    clinic_id: str,
    appointment_id: int,
    name: str,
    phone: str,
    appointment_date: str,
    appointment_time: str,
    reason: str,
):
    appointment = get_tenant_appointment(db, clinic_id, appointment_id)
    if appointment is None:
        raise ValueError("Appointment not found or access denied")

    appointment.name = name
    appointment.phone = phone
    appointment.date = appointment_date
    appointment.time = appointment_time
    appointment.reason = reason
    db.commit()
    return appointment


def delete_tenant_appointment(db: Session, clinic_id: str, appointment_id: int) -> None:
    appointment = get_tenant_appointment(db, clinic_id, appointment_id)
    if appointment is None:
        raise ValueError("Appointment not found or access denied")

    db.delete(appointment)
    db.commit()


def update_tenant_working_hours(db: Session, clinic_id: str, updated_hours: list[tuple[int, time, time]]) -> None:
    save_clinic_working_hours(db, clinic_id, updated_hours)


def update_tenant_appointment_duration(db: Session, clinic_id: str, duration: int) -> None:
    settings = get_clinic_settings(db, clinic_id)
    if settings is None:
        raise ValueError("Settings not found")

    settings.appointment_duration = duration
    db.commit()

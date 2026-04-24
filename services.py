from typing import List, Dict
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session
from database import Clinic, ClinicSettings, WorkingHours, Appointment


def get_clinic_by_api_key(db: Session, api_key: str):
    """Get clinic tenant from API key"""
    return db.query(Clinic).filter(Clinic.api_key == api_key).first()


def generate_time_slots(start_time: time, end_time: time, duration_minutes: int) -> List[str]:
    """Generate time slots between start and end time with given duration"""
    slots = []
    current = datetime.combine(datetime.today(), start_time)
    end_dt = datetime.combine(datetime.today(), end_time)

    while current + timedelta(minutes=duration_minutes) <= end_dt:
        slots.append(current.strftime("%H:%M"))
        current += timedelta(minutes=duration_minutes)

    return slots


def get_available_slots(db: Session, tenant_id: str, date_str: str) -> List[str]:
    """Get all available time slots for given tenant and date"""
    # Parse date and get day of week (0=Monday, 6=Sunday)
    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    day_of_week = date_obj.weekday()

    # Get clinic settings
    settings = db.query(ClinicSettings).filter(ClinicSettings.tenant_id == tenant_id).first()
    if not settings:
        return []

    # Get working hours for this day
    working_hours = db.query(WorkingHours).filter(
        WorkingHours.tenant_id == tenant_id,
        WorkingHours.day_of_week == day_of_week
    ).first()

    if not working_hours:
        return []

    # Generate all possible slots for this day
    all_slots = generate_time_slots(
        working_hours.start_time,
        working_hours.end_time,
        settings.appointment_duration
    )

    # Get already booked slots for this tenant and date
    booked_times = [
        booking.time for booking in db.query(Appointment)
        .filter(Appointment.tenant_id == tenant_id)
        .filter(Appointment.date == date_str)
        .all()
    ]

    # Filter out booked slots
    available = [slot for slot in all_slots if slot not in booked_times]

    return available


def check_availability(db: Session, tenant_id: str, date: str, time: str) -> bool:
    """Check if specific date and time slot is available for tenant with row locking"""
    existing = db.query(Appointment).filter(
        Appointment.tenant_id == tenant_id,
        Appointment.date == date,
        Appointment.time == time
    ).with_for_update().first()

    return existing is None


def book_appointment(db: Session, tenant_id: str, name: str, phone: str, date: str, time: str, reason: str) -> Dict:
    """Book an appointment after checking availability for tenant with transaction isolation"""
    
    # Use transaction to prevent race conditions
    try:
        # Start explicit transaction
        with db.begin_nested():
            # Check if slot is already booked with row lock
            if not check_availability(db, tenant_id, date, time):
                return {
                    "success": False,
                    "message": f"Slot {time} on {date} is already booked. Please choose another time."
                }

            # Create new booking
            booking = Appointment(
                tenant_id=tenant_id,
                name=name,
                phone=phone,
                date=date,
                time=time,
                reason=reason
            )

            db.add(booking)
        
        # Commit outer transaction
        db.commit()
        db.refresh(booking)

    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "message": f"Booking failed: {str(e)}"
        }

    return {
        "success": True,
        "message": "Appointment booked successfully",
        "booking_details": {
            "name": name,
            "phone": phone,
            "date": date,
            "time": time,
            "reason": reason
        }
    }


def get_current_time_for_tenant(tenant_id: str, db: Session) -> datetime:
    """Get current datetime in tenant's local timezone"""
    settings = db.query(ClinicSettings).filter(ClinicSettings.tenant_id == tenant_id).first()
    if not settings:
        return datetime.now(ZoneInfo("UTC"))

    return datetime.now(ZoneInfo(settings.timezone))
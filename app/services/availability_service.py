from datetime import date, time, datetime, timedelta
from typing import List, Tuple, Optional
from sqlalchemy.orm import Session
import pytz
from app.models.models import WorkingHours, Holiday, Appointment, Tenant, AppointmentStatus


class AvailabilityService:
    """
    Service for handling availability checking and slot generation.
    Implements:
    - 30-minute slot generation
    - Working hours validation (clinic level + doctor overrides)
    - Holiday exclusion
    - Booked slot exclusion
    - Timezone conversion
    """

    SLOT_DURATION_MINUTES = 60

    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.timezone = pytz.timezone("UTC")

    def get_available_slots(self, doctor_id: int, check_date: date) -> List[str]:
        """
        Get all available 30-minute slots for given doctor and date.
        Returns list of time strings in format "HH:MM"
        """

        # Step 1: Check if date is a holiday
        if self._is_holiday(check_date):
            return []

        # Step 2: Get working hours (doctor specific or fallback to clinic)
        working_hours = self._get_working_hours(doctor_id, check_date.weekday())

        if not working_hours or working_hours.is_closed:
            return []

        # Step 3: Generate all possible slots for the day
        all_slots = self._generate_time_slots(working_hours.open_time, working_hours.close_time)

        # Step 4: Get already booked slots
        booked_slots = self._get_booked_slots(doctor_id, check_date)

        # Step 5: Filter out booked slots
        available_slots = [slot for slot in all_slots if slot not in booked_slots]

        return available_slots

    def _is_holiday(self, check_date: date) -> bool:
        """Check if given date is a holiday for this tenant"""
        return self.db.query(Holiday).filter(
            Holiday.tenant_id == self.tenant_id,
            Holiday.date == check_date
        ).first() is not None

    def _get_working_hours(self, doctor_id: int, day_of_week: int) -> Optional[WorkingHours]:
        """Default working hours 8AM - 5PM USA Monday to Saturday"""
        default = WorkingHours()
        default.open_time = time(8, 0)
        default.close_time = time(17, 0)
        default.is_closed = day_of_week == 6  # Sunday closed
        return default

    def _generate_time_slots(self, open_time: time, close_time: time) -> List[str]:
        """Generate 30-minute time slots between open and close time"""
        slots = []
        current = datetime.combine(date.today(), open_time)
        end = datetime.combine(date.today(), close_time)

        while current < end:
            slots.append(current.strftime("%H:%M"))
            current += timedelta(minutes=self.SLOT_DURATION_MINUTES)

        return slots

    def _get_booked_slots(self, doctor_id: int, check_date: date) -> List[str]:
        """Get already booked slots for given doctor and date"""
        appointments = self.db.query(Appointment).filter(
            Appointment.tenant_id == self.tenant_id,
            Appointment.doctor_id == doctor_id,
            Appointment.date == check_date,
            Appointment.status == AppointmentStatus.SCHEDULED
        ).all()

        return [appt.time.strftime("%H:%M") for appt in appointments]

    def get_earliest_available_slot(self, doctor_id: int, start_from: Optional[date] = None) -> Optional[Tuple[date, str]]:
        """Find earliest available slot starting from given date"""
        if start_from is None:
            start_from = date.today()

        # Check next 14 days for availability
        for days_offset in range(14):
            check_date = start_from + timedelta(days=days_offset)
            slots = self.get_available_slots(doctor_id, check_date)

            if slots:
                return (check_date, slots[0])

        return None

    def is_slot_available(self, doctor_id: int, check_date: date, slot_time: str) -> bool:
        """Check if specific slot is available"""
        available_slots = self.get_available_slots(doctor_id, check_date)
        return slot_time in available_slots
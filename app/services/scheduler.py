from datetime import datetime, timedelta, time
from sqlalchemy.orm import Session
from app.db.models import WorkingHours, Holiday, Appointment, AppointmentType, Clinic, AppointmentStatus
import logging
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)


class Scheduler:
    def __init__(self, db: Session, clinic_id: int = 1):
        self.db = db
        self.clinic_id = clinic_id
        self.clinic = self.db.get(Clinic, clinic_id)

        # Auto create default clinic if not exists
        if not self.clinic:
            self.clinic = Clinic(
                id=clinic_id,
                name="Default Clinic",
                timezone="America/Los_Angeles"
            )
            self.db.add(self.clinic)
            self.db.commit()
            self.db.refresh(self.clinic)
            
        self.timezone = ZoneInfo(self.clinic.timezone)

    def local_to_utc(self, local_dt: datetime) -> datetime:
        """Convert clinic local time to UTC"""
        if local_dt.tzinfo is None:
            local_dt = local_dt.replace(tzinfo=self.timezone)
        return local_dt.astimezone(ZoneInfo("UTC"))

    def utc_to_local(self, utc_dt: datetime) -> datetime:
        """Convert UTC time to clinic local time"""
        if utc_dt.tzinfo is None:
            utc_dt = utc_dt.replace(tzinfo=ZoneInfo("UTC"))
        return utc_dt.astimezone(self.timezone)

    def get_available_slots(self, check_date, appointment_type_name, max_slots=5):
        if self._is_holiday(check_date):
            return []
            
        # Sunday blocking
        if check_date.weekday() == 6:
            return []

        working_hours = self._get_working_hours(check_date.weekday())
        if working_hours.is_closed:
            return []

        duration, buffer = self._get_appointment_type_settings(appointment_type_name)

        existing_appointments = self.db.query(Appointment).filter(
            Appointment.clinic_id == self.clinic_id,
            Appointment.date == check_date,
            Appointment.status == AppointmentStatus.BOOKED
        ).all()

        slots = []
        current_time = datetime.combine(check_date, working_hours.open_time)
        close_time = datetime.combine(check_date, working_hours.close_time)

        # Slot step at standard interval (not including buffer)
        slot_step = duration

        while current_time + timedelta(minutes=duration) <= close_time:
            conflict = False
            for apt in existing_appointments:
                if self._has_conflict(
                    check_date=check_date,
                    candidate_start=current_time,
                    candidate_duration=duration,
                    candidate_buffer=buffer,
                    existing_appointment=apt,
                ):
                    conflict = True
                    break

            if not conflict:
                slots.append(current_time.time())

            current_time += timedelta(minutes=slot_step)

        # Smart slot distribution - return balanced slots instead of first N
        if len(slots) <= max_slots:
            return slots

        # Return: earliest, mid slots, latest
        distributed = []
        distributed.append(slots[0])  # earliest

        step = len(slots) // (max_slots - 1)
        for i in range(1, max_slots - 1):
            idx = i * step
            if idx < len(slots):
                distributed.append(slots[idx])

        distributed.append(slots[-1])  # latest
        return distributed

    def is_slot_available(self, check_date, check_time, appointment_type_name):
        """Check single slot availability - used for final recheck"""
        duration, buffer = self._get_appointment_type_settings(appointment_type_name)
        check_start = datetime.combine(check_date, check_time)

        existing_appointments = self.db.query(Appointment).filter(
            Appointment.clinic_id == self.clinic_id,
            Appointment.date == check_date,
            Appointment.status == AppointmentStatus.BOOKED
        ).with_for_update().all()

        for apt in existing_appointments:
            if self._has_conflict(
                check_date=check_date,
                candidate_start=check_start,
                candidate_duration=duration,
                candidate_buffer=buffer,
                existing_appointment=apt,
            ):
                return False

        return True

    def _get_appointment_type_settings(self, appointment_type_name):
        appointment_type = self.db.query(AppointmentType).filter(
            AppointmentType.clinic_id == self.clinic_id,
            AppointmentType.name == appointment_type_name
        ).first()

        if not appointment_type:
            return self.clinic.default_duration_minutes, self.clinic.default_buffer_minutes

        return appointment_type.duration_minutes, appointment_type.buffer_minutes

    def _get_existing_buffer_minutes(self, appointment):
        if appointment.appointment_type and appointment.appointment_type.buffer_minutes is not None:
            return appointment.appointment_type.buffer_minutes
        return self.clinic.default_buffer_minutes

    def _has_conflict(self, check_date, candidate_start, candidate_duration, candidate_buffer, existing_appointment):
        existing_start = datetime.combine(check_date, existing_appointment.start_time)
        existing_end = datetime.combine(check_date, existing_appointment.end_time)
        existing_buffer = self._get_existing_buffer_minutes(existing_appointment)

        candidate_end_with_buffer = candidate_start + timedelta(
            minutes=candidate_duration + candidate_buffer
        )
        existing_end_with_buffer = existing_end + timedelta(minutes=existing_buffer)

        return candidate_start < existing_end_with_buffer and candidate_end_with_buffer > existing_start

    def _is_holiday(self, date):
        return self.db.query(Holiday).filter(
            Holiday.clinic_id == self.clinic_id,
            Holiday.date == date
        ).first() is not None

    def _get_working_hours(self, day_of_week):
        wh = self.db.query(WorkingHours).filter(
            WorkingHours.clinic_id == self.clinic_id,
            WorkingHours.day_of_week == day_of_week
        ).first()

        if not wh:
            return WorkingHours(
                clinic_id=self.clinic_id,
                day_of_week=day_of_week,
                open_time=time(9, 0),
                close_time=time(17, 0),
                is_closed=0
            )
        return wh

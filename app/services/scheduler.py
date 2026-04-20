from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from app.db.models import Appointment, AppointmentStatus, AppointmentType, Clinic, Holiday, WorkingHours


class Scheduler:
    def __init__(self, db: Session, clinic_id: int = 1):
        self.db = db
        self.clinic_id = clinic_id
        self.default_open = time(9, 0)
        self.default_close = time(17, 0)
        self.default_break_start = None
        self.default_break_end = None

    def get_available_slots(self, check_date, appointment_type_name: str, max_slots: int = 5):
        if self.get_unavailability_reason(check_date) is not None:
            return []

        working_hours = self._get_working_hours(check_date.weekday())
        appointment_type = self._get_or_build_appointment_type(appointment_type_name)
        duration = appointment_type.duration_minutes
        buffer = appointment_type.buffer_minutes

        existing_appointments = self.db.query(Appointment).filter(
            Appointment.clinic_id == self.clinic_id,
            Appointment.date == check_date,
            Appointment.status == AppointmentStatus.BOOKED,
        ).all()

        slots = []
        current_start = datetime.combine(check_date, working_hours.open_time)
        close_time = datetime.combine(check_date, working_hours.close_time)
        break_start = working_hours.break_start or self.default_break_start
        break_end = working_hours.break_end or self.default_break_end
        slot_step = timedelta(minutes=duration + buffer)

        break_start_dt = None
        break_end_dt = None
        if break_start is not None and break_end is not None:
            break_start_dt = datetime.combine(check_date, break_start)
            break_end_dt = datetime.combine(check_date, break_end)

        while current_start + timedelta(minutes=duration) <= close_time:
            candidate_end = current_start + timedelta(minutes=duration)

            overlaps_break = (
                break_start_dt is not None
                and break_end_dt is not None
                and current_start < break_end_dt
                and candidate_end > break_start_dt
            )
            has_conflict = any(
                self._has_conflict(current_start, candidate_end, appointment, buffer)
                for appointment in existing_appointments
            )

            if not overlaps_break and not has_conflict:
                slots.append(current_start.time())

            if overlaps_break and break_end_dt is not None and current_start < break_end_dt:
                current_start = break_end_dt
            else:
                current_start += slot_step

        return slots[:max_slots]

    def is_bookable_date(self, check_date: date):
        return self._get_date_limit_reason(check_date) is None

    def get_unavailability_reason(self, check_date: date):
        date_limit_reason = self._get_date_limit_reason(check_date)
        if date_limit_reason is not None:
            return date_limit_reason

        holiday = self._get_holiday(check_date)
        if holiday is not None:
            if holiday.reason:
                return f"Clinic is closed on {check_date.isoformat()} for {holiday.reason}"
            return f"Clinic is closed on {check_date.isoformat()}"

        working_hours = self._get_working_hours(check_date.weekday())
        if working_hours.is_closed:
            return f"Clinic is closed on {check_date.strftime('%A')}"

        return None

    def _get_date_limit_reason(self, check_date: date):
        today = date.today()
        clinic = self._get_clinic()
        latest_allowed = today + timedelta(days=clinic.max_booking_days)

        if check_date < today:
            return "Past dates cannot be booked"

        if check_date > latest_allowed:
            return f"Bookings are only available through {latest_allowed.isoformat()}"

        return None

    def _get_or_build_appointment_type(self, appointment_type_name: str):
        appointment_type = self.db.query(AppointmentType).filter(
            AppointmentType.clinic_id == self.clinic_id,
            AppointmentType.name == appointment_type_name,
        ).first()

        if appointment_type:
            return appointment_type

        return AppointmentType(
            clinic_id=self.clinic_id,
            name=appointment_type_name,
            duration_minutes=60,
            buffer_minutes=5,
        )

    def _has_conflict(self, candidate_start: datetime, candidate_end: datetime, appointment: Appointment, buffer: int):
        existing_start = datetime.combine(appointment.date, appointment.start_time)
        existing_end = datetime.combine(appointment.date, appointment.end_time) + timedelta(minutes=buffer)
        return candidate_start < existing_end and candidate_end > existing_start

    def _is_holiday(self, check_date):
        return self._get_holiday(check_date) is not None

    def _get_holiday(self, check_date):
        return self.db.query(Holiday).filter(
            Holiday.clinic_id == self.clinic_id,
            Holiday.date == check_date,
        ).first()

    def _get_clinic(self):
        clinic = self.db.query(Clinic).filter(Clinic.id == self.clinic_id).first()
        if clinic:
            return clinic

        clinic = Clinic(id=self.clinic_id, name=f"Clinic {self.clinic_id}")
        self.db.add(clinic)
        self.db.commit()
        self.db.refresh(clinic)
        return clinic

    def _get_working_hours(self, day_of_week: int):
        working_hours = self.db.query(WorkingHours).filter(
            WorkingHours.clinic_id == self.clinic_id,
            WorkingHours.day_of_week == day_of_week,
        ).first()

        if working_hours:
            return working_hours

        is_closed = 1 if day_of_week >= 5 else 0
        return WorkingHours(
            clinic_id=self.clinic_id,
            day_of_week=day_of_week,
            open_time=self.default_open,
            close_time=self.default_close,
            break_start=None,
            break_end=None,
            is_closed=is_closed,
        )

from datetime import datetime, timedelta, time
from sqlalchemy.orm import Session
from app.db.models import WorkingHours, Holiday, Appointment, AppointmentType


class Scheduler:
    def __init__(self, db: Session, clinic_id: int = 1):
        self.db = db
        self.default_open = time(9, 0)
        self.default_close = time(17, 0)

    def get_available_slots(self, tenant_id, check_date, appointment_type_name, max_slots=5):
        if self._is_holiday(tenant_id, check_date):
            return []

        working_hours = self._get_working_hours(tenant_id, check_date.weekday())
        if working_hours.is_closed:
            return []

        appointment_type = self.db.query(AppointmentType).filter(
            AppointmentType.name == appointment_type_name
        ).first()

        if not appointment_type:
            appointment_type = AppointmentType(
                name=appointment_type_name,
                duration_minutes=60,
                buffer_minutes=5
            )

        duration = appointment_type.duration_minutes
        buffer = appointment_type.buffer_minutes

        existing_appointments = self.db.query(Appointment).filter(
            Appointment.tenant_id == tenant_id,
            Appointment.date == check_date,
            Appointment.status == "scheduled"
        ).all()

        slots = []
        current_time = datetime.combine(check_date, working_hours.open_time)
        close_time = datetime.combine(check_date, working_hours.close_time)
        
        # Get break times
        break_start = working_hours.break_start or self.default_break_start
        break_end = working_hours.break_end or self.default_break_end
        break_start_dt = datetime.combine(check_date, break_start)
        break_end_dt = datetime.combine(check_date, break_end)

        # Slot step at standard interval (not including buffer)
        slot_step = duration

        while current_time + timedelta(minutes=duration) <= close_time:
            slot_end = current_time + timedelta(minutes=duration)

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

    def _is_holiday(self, tenant_id, date):
        return self.db.query(Holiday).filter(
            Holiday.tenant_id == tenant_id,
            Holiday.date == date
        ).first() is not None

    def _get_working_hours(self, day_of_week):
        wh = self.db.query(WorkingHours).filter(
            WorkingHours.tenant_id == tenant_id,
            WorkingHours.day_of_week == day_of_week
        ).first()

        if not wh:
            # Weekdays (0=Monday, 1=Tuesday, 2=Wednesday, 3=Thursday, 4=Friday) are open
            # Saturday (5) and Sunday (6) are closed
            is_closed = 1 if day_of_week >= 5 else 0
            
            return WorkingHours(
                clinic_id=self.clinic_id,
                day_of_week=day_of_week,
                open_time=self.default_open,
                close_time=self.default_close,
                is_closed=0
            )
        return wh

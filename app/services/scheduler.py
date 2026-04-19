from datetime import datetime, timedelta, time
from sqlalchemy.orm import Session
from app.db.models import WorkingHours, Holiday, Appointment, AppointmentType


class Scheduler:
    def __init__(self, db: Session):
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

        slot_step = duration + buffer

        while current_time + timedelta(minutes=duration) <= close_time:
            slot_end = current_time + timedelta(minutes=duration)

            conflict = False
            for apt in existing_appointments:
                apt_start = datetime.combine(check_date, apt.start_time)
                apt_end = datetime.combine(check_date, apt.end_time)

                if (current_time < apt_end) and (slot_end > apt_start):
                    conflict = True
                    break

            if not conflict:
                slots.append(current_time.time())
                if len(slots) >= max_slots:
                    break

            current_time += timedelta(minutes=slot_step)

        return slots

    def _is_holiday(self, tenant_id, date):
        return self.db.query(Holiday).filter(
            Holiday.tenant_id == tenant_id,
            Holiday.date == date
        ).first() is not None

    def _get_working_hours(self, tenant_id, day_of_week):
        wh = self.db.query(WorkingHours).filter(
            WorkingHours.tenant_id == tenant_id,
            WorkingHours.day_of_week == day_of_week
        ).first()

        if not wh:
            return WorkingHours(
                day_of_week=day_of_week,
                open_time=self.default_open,
                close_time=self.default_close,
                is_closed=0
            )
        return wh
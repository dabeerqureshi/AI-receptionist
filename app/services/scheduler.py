from datetime import datetime, timedelta, time
from sqlalchemy.orm import Session
from app.db.models import WorkingHours, Appointment


class Scheduler:
    def __init__(self, db: Session):
        self.db = db
        self.default_open = time(8, 0)
        self.default_close = time(17, 0)
        self.default_break_start = time(13, 0)
        self.default_break_end = time(14, 0)

    def get_available_slots(self, check_date, max_slots=5):
        working_hours = self._get_working_hours(check_date.weekday())
        if working_hours.is_closed:
            return []

        # Fixed duration for all appointments
        duration = 60
        buffer = 5

        existing_appointments = self.db.query(Appointment).filter(
            Appointment.date == check_date
        ).all()

        slots = []
        current_time = datetime.combine(check_date, working_hours.open_time)
        close_time = datetime.combine(check_date, working_hours.close_time)
        
        # Get break times
        break_start = working_hours.break_start or self.default_break_start
        break_end = working_hours.break_end or self.default_break_end
        break_start_dt = datetime.combine(check_date, break_start)
        break_end_dt = datetime.combine(check_date, break_end)

        slot_step = duration + buffer

        while current_time + timedelta(minutes=duration) <= close_time:
            slot_end = current_time + timedelta(minutes=duration)
            
            # Skip slots that overlap with break time
            if (current_time < break_end_dt) and (slot_end > break_start_dt):
                current_time = break_end_dt
                continue

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


    def _get_working_hours(self, day_of_week):
        wh = self.db.query(WorkingHours).filter(
            WorkingHours.day_of_week == day_of_week
        ).first()

        if not wh:
            # Weekdays (0=Monday, 1=Tuesday, 2=Wednesday, 3=Thursday, 4=Friday) are open
            # Saturday (5) and Sunday (6) are closed
            is_closed = 1 if day_of_week >= 5 else 0
            
            return WorkingHours(
                day_of_week=day_of_week,
                open_time=self.default_open,
                close_time=self.default_close,
                break_start=self.default_break_start,
                break_end=self.default_break_end,
                is_closed=is_closed
            )
        return wh

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.db.models import Appointment
from app.services.scheduler import Scheduler


class BookingService:
    def __init__(self, db: Session):
        self.db = db
        self.scheduler = Scheduler(db)

    def book_appointment(self, name, phone, appointment_date, appointment_time, notes=None):
        available_slots = self.scheduler.get_available_slots(
            appointment_date,
            max_slots=100
        )

        if appointment_time not in available_slots:
            return None, "This time slot is no longer available"

        # Fixed 60 minute appointments
        end_time = (datetime.combine(appointment_date, appointment_time) +
                   timedelta(minutes=60)).time()

        appointment = Appointment(
            patient_name=name,
            patient_phone=phone,
            date=appointment_date,
            start_time=appointment_time,
            end_time=end_time,
            notes=notes
        )

        self.db.add(appointment)
        self.db.commit()
        self.db.refresh(appointment)

        return appointment, f"Appointment confirmed for {appointment_date} at {appointment_time}"
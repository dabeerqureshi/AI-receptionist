from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.db.models import Patient, Appointment, AppointmentType
from app.services.scheduler import Scheduler


class BookingService:
    def __init__(self, db: Session):
        self.db = db
        self.scheduler = Scheduler(db)

    def book_appointment(self, tenant_id, name, phone, appointment_date, appointment_time, appointment_type_name, notes=None):
        appointment_type = self.db.query(AppointmentType).filter(
            AppointmentType.name == appointment_type_name
        ).first()

        if not appointment_type:
            appointment_type = AppointmentType(
                name=appointment_type_name,
                duration_minutes=60,
                buffer_minutes=5
            )
            self.db.add(appointment_type)
            self.db.commit()
            self.db.refresh(appointment_type)

        available_slots = self.scheduler.get_available_slots(
            tenant_id,
            appointment_date,
            appointment_type_name,
            max_slots=100
        )

        if appointment_time not in available_slots:
            return None, "This time slot is no longer available"

        patient = self.db.query(Patient).filter(Patient.phone == phone).first()
        if not patient:
            patient = Patient(name=name, phone=phone)
            self.db.add(patient)
            self.db.commit()
            self.db.refresh(patient)

        end_time = (datetime.combine(appointment_date, appointment_time) +
                   timedelta(minutes=appointment_type.duration_minutes)).time()

        appointment = Appointment(
            tenant_id=tenant_id,
            patient_id=patient.id,
            appointment_type_id=appointment_type.id,
            date=appointment_date,
            start_time=appointment_time,
            end_time=end_time,
            status="scheduled",
            notes=notes
        )

        self.db.add(appointment)
        self.db.commit()
        self.db.refresh(appointment)

        return appointment, f"Appointment confirmed for {appointment_date} at {appointment_time}"
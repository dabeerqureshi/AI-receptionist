from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.db.models import Patient, Appointment, AppointmentType
from app.services.scheduler import Scheduler
import logging
import json

logger = logging.getLogger(__name__)


class BookingService:
    def __init__(self, db: Session, clinic_id: int = 1):
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
            appointment_date,
            max_slots=100
        )

        if appointment_time not in available_slots:
            logger.warning(f"Slot conflict detected: {appointment_date} {appointment_time}")
            return None, "This time slot is no longer available"

        patient = self.db.query(Patient).filter(Patient.phone == phone).first()
        if not patient:
            patient = Patient(name=name, phone=phone)
            self.db.add(patient)
            self.db.commit()
            self.db.refresh(patient)

        end_time = (datetime.combine(appointment_date, appointment_time) +
                   timedelta(minutes=60)).time()

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
            transaction.commit()
            self.db.refresh(appointment)

            logger.info(f"Appointment booked successfully: {appointment.id}")
            
            result = {
                "appointment": appointment,
                "message": f"Appointment confirmed for {appointment_date} at {appointment_time}"
            }

            self.store_idempotency_result(idempotency_key, result)
            
            return appointment, result["message"]

        except IntegrityError:
            self.db.rollback()
            logger.warning(f"Slot lost to concurrent booking: {appointment_date} {appointment_time}")
            return None, "This time slot was just taken, please select another"
        except Exception as e:
            self.db.rollback()
            logger.error(f"Booking failed with error: {str(e)}", exc_info=True)
            return None, "Failed to book appointment. Please try again."

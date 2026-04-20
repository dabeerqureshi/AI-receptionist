import json
import logging
from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Appointment, AppointmentStatus, AppointmentType, IdempotencyKey, Patient
from app.services.scheduler import Scheduler

logger = logging.getLogger(__name__)


class BookingService:
    def __init__(self, db: Session, clinic_id: int = 1):
        self.db = db
        self.clinic_id = clinic_id
        self.scheduler = Scheduler(db, clinic_id=clinic_id)

    def book_appointment(self, name, phone, appointment_date, appointment_time, appointment_type_name, notes=None, idempotency_key=None):
        if idempotency_key:
            cached_response = self._get_idempotent_response(idempotency_key)
            if cached_response is not None:
                return cached_response

        unavailability_reason = self.scheduler.get_unavailability_reason(appointment_date)
        if unavailability_reason is not None:
            response = self._build_failure_response(unavailability_reason)
            self._store_idempotent_response(idempotency_key, response)
            return response

        appointment_type = self.db.query(AppointmentType).filter(
            AppointmentType.clinic_id == self.clinic_id,
            AppointmentType.name == appointment_type_name,
        ).first()

        if not appointment_type:
            appointment_type = AppointmentType(
                clinic_id=self.clinic_id,
                name=appointment_type_name,
                duration_minutes=60,
                buffer_minutes=5,
            )
            self.db.add(appointment_type)
            self.db.commit()
            self.db.refresh(appointment_type)

        available_slots = self.scheduler.get_available_slots(
            check_date=appointment_date,
            appointment_type_name=appointment_type_name,
            max_slots=1000,
        )

        if appointment_time not in available_slots:
            logger.warning("Slot conflict detected for %s %s", appointment_date, appointment_time)
            response = self._build_failure_response("This time slot is no longer available")
            self._store_idempotent_response(idempotency_key, response)
            return response

        patient = self.db.query(Patient).filter(
            Patient.clinic_id == self.clinic_id,
            Patient.phone == phone,
        ).first()
        if not patient:
            patient = Patient(clinic_id=self.clinic_id, name=name, phone=phone)
            self.db.add(patient)
            self.db.commit()
            self.db.refresh(patient)

        end_time = (
            datetime.combine(appointment_date, appointment_time)
            + timedelta(minutes=appointment_type.duration_minutes)
        ).time()

        appointment = Appointment(
            clinic_id=self.clinic_id,
            patient_id=patient.id,
            appointment_type_id=appointment_type.id,
            date=appointment_date,
            start_time=appointment_time,
            end_time=end_time,
            status=AppointmentStatus.BOOKED,
            notes=notes,
        )

        try:
            self.db.add(appointment)
            self.db.commit()
            self.db.refresh(appointment)
            logger.info("Appointment booked successfully: %s", appointment.id)
            response = {
                "success": True,
                "data": {
                    "confirmation_id": appointment.id,
                    "date": appointment_date.isoformat(),
                    "time": appointment_time.strftime("%H:%M"),
                },
                "message": f"Appointment confirmed for {appointment_date} at {appointment_time.strftime('%H:%M')}",
            }
            self._store_idempotent_response(idempotency_key, response)
            return response
        except IntegrityError:
            self.db.rollback()
            logger.warning("Slot lost to concurrent booking for %s %s", appointment_date, appointment_time)
            response = self._build_failure_response("This time slot was just taken, please select another")
            self._store_idempotent_response(idempotency_key, response)
            return response
        except Exception:
            self.db.rollback()
            logger.exception("Booking failed")
            response = self._build_failure_response("Failed to book appointment. Please try again.")
            self._store_idempotent_response(idempotency_key, response)
            return response

    def _get_idempotent_response(self, idempotency_key: str):
        record = self.db.query(IdempotencyKey).filter(IdempotencyKey.key == idempotency_key).first()
        if not record:
            return None
        return json.loads(record.response)

    def _store_idempotent_response(self, idempotency_key: str | None, response: dict):
        if not idempotency_key:
            return

        record = self.db.query(IdempotencyKey).filter(IdempotencyKey.key == idempotency_key).first()
        payload = json.dumps(response)

        if record:
            record.response = payload
        else:
            record = IdempotencyKey(key=idempotency_key, response=payload)
            self.db.add(record)

        self.db.commit()

    def _build_failure_response(self, message: str):
        return {
            "success": False,
            "data": None,
            "message": message,
        }

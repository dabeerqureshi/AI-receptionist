from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.db.models import Patient, Appointment, AppointmentType, Clinic, IdempotencyKey, AppointmentStatus
from app.services.scheduler import Scheduler
import logging
import json

logger = logging.getLogger(__name__)


class BookingService:
    def __init__(self, db: Session, clinic_id: int = 1):
        self.db = db
        self.clinic_id = clinic_id
        self.scheduler = Scheduler(db, clinic_id)
        self.clinic = self.scheduler.clinic

    def check_idempotency(self, idempotency_key: str):
        """Check for existing idempotency key"""
        if not idempotency_key:
            return None
        
        existing = self.db.query(IdempotencyKey).filter(
            IdempotencyKey.key == idempotency_key,
            IdempotencyKey.created_at > datetime.utcnow() - timedelta(hours=24)
        ).first()
        
        if existing:
            return json.loads(existing.response)
        return None

    def store_idempotency_result(self, idempotency_key: str, result: dict):
        """Store result for idempotency"""
        if not idempotency_key:
            return
        
        key = IdempotencyKey(
            key=idempotency_key,
            response=json.dumps(result)
        )
        self.db.add(key)
        self.db.commit()

    def validate_booking_date(self, appointment_date):
        """Validate booking date"""
        today = datetime.utcnow().date()
        
        if appointment_date < today:
            return False, "Cannot book appointments in the past"
        
        # Sunday check
        if appointment_date.weekday() == 6:
            return False, "Bookings are not allowed on Sundays"
        
        # Holiday check
        if self.scheduler._is_holiday(appointment_date):
            return False, "Clinic is closed on this holiday date"
        
        max_date = today + timedelta(days=self.clinic.max_booking_days)
        if appointment_date > max_date:
            return False, f"Bookings are only allowed up to {self.clinic.max_booking_days} days in advance"
        
        return True, None

    def book_appointment(self, name, phone, appointment_date, appointment_time, appointment_type_name, notes=None, idempotency_key=None):
        logger.info(f"Booking attempt: {phone} for {appointment_date} {appointment_time}")

        # Idempotency check
        cached = self.check_idempotency(idempotency_key)
        if cached:
            logger.info(f"Idempotency hit, returning cached result for key: {idempotency_key}")
            return cached.get('appointment'), cached.get('message')

        # Date validation
        date_valid, error = self.validate_booking_date(appointment_date)
        if not date_valid:
            logger.warning(f"Booking failed date validation: {error}")
            return None, error

        # Get appointment type
        appointment_type = self.db.query(AppointmentType).filter(
            AppointmentType.clinic_id == self.clinic_id,
            AppointmentType.name == appointment_type_name
        ).first()

        if not appointment_type:
            appointment_type = AppointmentType(
                clinic_id=self.clinic_id,
                name=appointment_type_name,
                duration_minutes=self.clinic.default_duration_minutes,
                buffer_minutes=self.clinic.default_buffer_minutes
            )
            self.db.add(appointment_type)
            try:
                self.db.commit()
                self.db.refresh(appointment_type)
            except IntegrityError:
                self.db.rollback()
                appointment_type = self.db.query(AppointmentType).filter(
                    AppointmentType.clinic_id == self.clinic_id,
                    AppointmentType.name == appointment_type_name
                ).first()

        # Check slot availability
        available_slots = self.scheduler.get_available_slots(
            appointment_date,
            appointment_type_name,
            max_slots=100
        )

        if appointment_time not in available_slots:
            logger.warning(f"Slot conflict detected: {appointment_date} {appointment_time}")
            return None, "This time slot is no longer available"

        # Patient deduplication (per clinic)
        patient = self.db.query(Patient).filter(
            Patient.clinic_id == self.clinic_id,
            Patient.phone == phone
        ).first()
        
        if not patient:
            patient = Patient(
                clinic_id=self.clinic_id,
                name=name,
                phone=phone
            )
            self.db.add(patient)
            self.db.commit()
            self.db.refresh(patient)
            logger.info(f"Created new patient: {patient.id}")
        else:
            # Update name if changed
            if patient.name != name:
                patient.name = name
                self.db.commit()
            logger.info(f"Found existing patient: {patient.id}")

        end_time = (datetime.combine(appointment_date, appointment_time) +
                   timedelta(minutes=appointment_type.duration_minutes)).time()

        # Start transaction with final recheck (race condition protection)
        try:
            # Explicitly create new transaction
            transaction = self.db.begin_nested()
            
            # FINAL SLOT CHECK RIGHT BEFORE INSERT (inside transaction with proper locking)
            # This is the last line of defense
            slot_available = self.scheduler.is_slot_available(
                appointment_date,
                appointment_time,
                appointment_type_name
            )

            if not slot_available:
                transaction.rollback()
                logger.error(f"Slot was taken during transaction: {appointment_date} {appointment_time}")
                return None, "This time slot was just taken, please select another"

            appointment = Appointment(
                clinic_id=self.clinic_id,
                patient_id=patient.id,
                appointment_type_id=appointment_type.id,
                date=appointment_date,
                start_time=appointment_time,
                end_time=end_time,
                status=AppointmentStatus.BOOKED,
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

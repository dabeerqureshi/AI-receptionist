from datetime import date, time, datetime
from sqlalchemy.orm import Session
from app.models.models import Appointment, AppointmentStatus
from app.services.availability_service import AvailabilityService
import logging

logger = logging.getLogger(__name__)


class BookingService:
    """
    Service for handling appointment booking, cancellation and rescheduling.
    All operations are tenant-isolated and validate availability before changes.
    """

    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.availability_service = AvailabilityService(db, tenant_id)

    def book_appointment(self, doctor_id: int, patient_name: str, appointment_date: date,
                        appointment_time: str, patient_phone: str = None, notes: str = None):
        """
        Book a new appointment.
        Checks for double booking before creating appointment.
        """

        # Validate slot is available first
        if not self.availability_service.is_slot_available(doctor_id, appointment_date, appointment_time):
            return {
                "success": False,
                "message": "Selected time slot is not available"
            }

        try:
            # Parse time string to time object
            appt_time = datetime.strptime(appointment_time, "%H:%M").time()

            # Create appointment record
            appointment = Appointment(
                tenant_id=self.tenant_id,
                doctor_id=doctor_id,
                patient_name=patient_name,
                patient_phone=patient_phone,
                date=appointment_date,
                time=appt_time,
                status=AppointmentStatus.SCHEDULED,
                notes=notes
            )

            self.db.add(appointment)
            self.db.commit()
            self.db.refresh(appointment)

            logger.info(f"Appointment booked successfully: ID {appointment.id}")

            return {
                "success": True,
                "appointment_id": appointment.id,
                "message": "Appointment booked successfully"
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error booking appointment: {str(e)}")
            return {
                "success": False,
                "message": f"Error booking appointment: {str(e)}"
            }

    def cancel_appointment(self, appointment_id: int):
        """Cancel an existing appointment"""
        appointment = self.db.query(Appointment).filter(
            Appointment.tenant_id == self.tenant_id,
            Appointment.id == appointment_id
        ).first()

        if not appointment:
            return {
                "success": False,
                "message": "Appointment not found"
            }

        appointment.status = AppointmentStatus.CANCELLED
        self.db.commit()

        logger.info(f"Appointment cancelled: ID {appointment_id}")

        return {
            "success": True,
            "message": "Appointment cancelled successfully"
        }

    def reschedule_appointment(self, appointment_id: int, new_date: date, new_time: str):
        """Reschedule an existing appointment to new date/time"""
        appointment = self.db.query(Appointment).filter(
            Appointment.tenant_id == self.tenant_id,
            Appointment.id == appointment_id
        ).first()

        if not appointment:
            return {
                "success": False,
                "message": "Appointment not found"
            }

        if appointment.status == AppointmentStatus.CANCELLED:
            return {
                "success": False,
                "message": "Cannot reschedule cancelled appointment"
            }

        # Validate new slot is available
        if not self.availability_service.is_slot_available(appointment.doctor_id, new_date, new_time):
            return {
                "success": False,
                "message": "Selected new time slot is not available"
            }

        try:
            appt_time = datetime.strptime(new_time, "%H:%M").time()

            appointment.date = new_date
            appointment.time = appt_time

            self.db.commit()

            logger.info(f"Appointment rescheduled: ID {appointment_id} to {new_date} {new_time}")

            return {
                "success": True,
                "message": "Appointment rescheduled successfully"
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error rescheduling appointment: {str(e)}")
            return {
                "success": False,
                "message": f"Error rescheduling appointment: {str(e)}"
            }

    def get_tenant_appointments(self):
        """Get all appointments for current tenant"""
        return self.db.query(Appointment).filter(
            Appointment.tenant_id == self.tenant_id
        ).order_by(Appointment.date, Appointment.time).all()
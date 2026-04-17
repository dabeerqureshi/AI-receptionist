from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.schemas import *
from app.services.availability_service import AvailabilityService
from app.services.booking_service import BookingService
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/check-availability")
def check_availability(
    http_request: Request,
    request: AvailabilityRequest,
    db: Session = Depends(get_db)
):
    """Check if requested time slot is available"""
    tenant_id = http_request.state.tenant_id
    logger.info(f"Tenant:{tenant_id} Checking availability for {request.date} {request.time}")
    availability_service = AvailabilityService(db, tenant_id)
    
    available = availability_service.is_slot_available(1, request.date, request.time)
    
    return {
        "available": available,
        "message": "Slot is available" if available else "Slot is not available"
    }


@router.post("/book-appointment")
def book_appointment(
    http_request: Request,
    request: BookingRequest,
    db: Session = Depends(get_db)
):
    """Book a new appointment"""
    tenant_id = http_request.state.tenant_id
    logger.info(f"Tenant:{tenant_id} Booking appointment for {request.patient_name}")
    booking_service = BookingService(db, tenant_id)
    
    result = booking_service.book_appointment(
        doctor_id=1,
        patient_name=request.patient_name,
        patient_phone=request.patient_phone,
        appointment_date=request.date,
        appointment_time=request.time
    )

    return result

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.requests import BookAppointmentRequest
from app.services.booking_service import BookingService

router = APIRouter(prefix="/api/v1", tags=["booking"])


@router.post("/book-appointment")
def book_appointment(
    request: BookAppointmentRequest,
    db: Session = Depends(get_db),
    clinic_id: int = 1,
    x_idempotency_key: str | None = Header(default=None),
):
    booking_service = BookingService(db, clinic_id=clinic_id)
    idempotency_key = x_idempotency_key if isinstance(x_idempotency_key, str) else None

    return booking_service.book_appointment(
        name=request.patient_name,
        phone=request.patient_phone,
        appointment_date=request.date,
        appointment_time=request.time,
        appointment_type_name=request.appointment_type,
        notes=request.notes,
        idempotency_key=idempotency_key,
    )

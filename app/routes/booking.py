from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.requests import BookAppointmentRequest
from app.services.booking_service import BookingService

router = APIRouter(prefix="/api/v1", tags=["booking"])


@router.post("/book-appointment")
def book_appointment(request: BookAppointmentRequest, db: Session = Depends(get_db), x_idempotency_key: str = None, clinic_id: int = 1):
    booking_service = BookingService(db, clinic_id=clinic_id)

    appointment, message = booking_service.book_appointment(
        name=request.patient_name,
        phone=request.patient_phone,
        appointment_date=appointment_date,
        appointment_time=appointment_time,
        appointment_type_name=request.appointment_type,
        notes=request.notes
    )

    if not appointment:
        return {
            "success": False,
            "data": None,
            "message": message
        }

    return {
        "success": True,
        "data": {
            "confirmation_id": appointment.id,
            "date": request.date.isoformat(),
            "time": request.time.strftime("%H:%M"),
        },
        "message": message,
    }

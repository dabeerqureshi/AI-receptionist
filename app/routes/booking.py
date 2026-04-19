from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.requests import BookAppointmentRequest
from app.services.booking_service import BookingService

router = APIRouter(prefix="/api/v1", tags=["booking"])


@router.post("/book-appointment")
def book_appointment(request: BookAppointmentRequest, db: Session = Depends(get_db)):
    booking_service = BookingService(db)
    
    # Parse date and time strings
    from datetime import datetime
    appointment_date = datetime.strptime(request.date, "%Y-%m-%d").date()
    
    # Handle both time formats: HH:MM and HH:MM:SS
    try:
        appointment_time = datetime.strptime(request.time, "%H:%M:%S").time()
    except ValueError:
        appointment_time = datetime.strptime(request.time, "%H:%M").time()

    appointment, message = booking_service.book_appointment(
        name=request.patient_name,
        phone=request.patient_phone,
        appointment_date=appointment_date,
        appointment_time=appointment_time,
        notes=request.notes
    )

    if not appointment:
        raise HTTPException(status_code=400, detail=message)

    return {
        "success": True,
        "confirmation_id": appointment.id,
        "message": message,
        "date": request.date,
        "time": request.time
    }

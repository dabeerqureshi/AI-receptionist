from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.requests import CheckAvailabilityRequest
from app.services.scheduler import Scheduler

router = APIRouter(prefix="/api/v1", tags=["availability"])


@router.post("/check-availability")
def check_availability(request: CheckAvailabilityRequest, db: Session = Depends(get_db), clinic_id: int = 1):
    scheduler = Scheduler(db, clinic_id=clinic_id)
    unavailability_reason = scheduler.get_unavailability_reason(request.date)
    slots = scheduler.get_available_slots(
        check_date=request.date,
        appointment_type_name=request.appointment_type,
        max_slots=5,
    )

    if unavailability_reason is not None:
        message = unavailability_reason
    elif slots:
        message = "Available slots retrieved successfully"
    else:
        message = "No available slots for the selected date"

    return {
        "clinic_id": clinic_id,
        "date": request.date,
        "appointment_type": request.appointment_type,
        "available_slots": slots,
        "message": message,
    }

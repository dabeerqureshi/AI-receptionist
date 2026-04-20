from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.requests import CheckAvailabilityRequest
from app.services.scheduler import Scheduler

router = APIRouter(prefix="/api/v1", tags=["availability"])


@router.post("/check-availability")
def check_availability(request: CheckAvailabilityRequest, db: Session = Depends(get_db), clinic_id: int = 1):
    scheduler = Scheduler(db, clinic_id=clinic_id)
    slots = scheduler.get_available_slots(
        check_date=request.date,
        max_slots=5
    )

    return {
        "tenant_id": request.tenant_id,
        "date": request.date,
        "appointment_type": request.appointment_type,
        "available_slots": slots
    }

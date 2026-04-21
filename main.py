from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import SessionLocal, Clinic, ClinicSettings, WorkingHours
from services import get_clinic_by_api_key, get_available_slots, book_appointment

app = FastAPI(title="AI Receptionist API", version="2.0")


# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Tenant authentication dependency
async def get_tenant(x_api_key: str = Header(...), db: Session = Depends(get_db)):
    clinic = get_clinic_by_api_key(db, x_api_key)
    if not clinic:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return clinic


class AvailabilityRequest(BaseModel):
    date: str


class BookingRequest(BaseModel):
    name: str
    phone: str
    date: str
    time: str
    reason: str


@app.get("/")
def root():
    return {"message": "AI Receptionist Multi-Tenant API"}


@app.post("/check-availability")
def check_date_availability(
    request: AvailabilityRequest,
    clinic: Clinic = Depends(get_tenant),
    db: Session = Depends(get_db)
):
    slots = get_available_slots(db, clinic.id, request.date)
    return {
        "tenant_id": clinic.id,
        "clinic_name": clinic.name,
        "date": request.date,
        "available_slots": slots
    }


@app.post("/book-appointment")
def create_booking(
    request: BookingRequest,
    clinic: Clinic = Depends(get_tenant),
    db: Session = Depends(get_db)
):
    result = book_appointment(
        db=db,
        tenant_id=clinic.id,
        name=request.name,
        phone=request.phone,
        date=request.date,
        time=request.time,
        reason=request.reason
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@app.get("/clinic/settings")
def get_clinic_settings(
    clinic: Clinic = Depends(get_tenant),
    db: Session = Depends(get_db)
):
    settings = db.query(ClinicSettings).filter(ClinicSettings.tenant_id == clinic.id).first()
    working_hours = db.query(WorkingHours).filter(WorkingHours.tenant_id == clinic.id).all()

    return {
        "clinic_id": clinic.id,
        "name": clinic.name,
        "timezone": settings.timezone if settings else "UTC",
        "appointment_duration": settings.appointment_duration if settings else 30,
        "working_hours": [
            {
                "day_of_week": wh.day_of_week,
                "start_time": wh.start_time.strftime("%H:%M"),
                "end_time": wh.end_time.strftime("%H:%M")
            } for wh in working_hours
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
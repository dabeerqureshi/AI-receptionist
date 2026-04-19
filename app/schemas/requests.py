from pydantic import BaseModel
from datetime import date, time


class CheckAvailabilityRequest(BaseModel):
    date: date


class BookAppointmentRequest(BaseModel):
    patient_name: str
    patient_phone: str
    date: str
    time: str
    notes: str | None = None

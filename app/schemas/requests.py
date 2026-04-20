from pydantic import BaseModel
from datetime import date, time


class CheckAvailabilityRequest(BaseModel):
    date: date
    appointment_type: str


class BookAppointmentRequest(BaseModel):
    patient_name: str
    patient_phone: str
    date: str
    time: str
    appointment_type: str
    notes: str | None = None

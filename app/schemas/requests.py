from datetime import date, time

from pydantic import BaseModel, Field


class CheckAvailabilityRequest(BaseModel):
    date: date
    appointment_type: str = Field(min_length=1)


class BookAppointmentRequest(BaseModel):
    patient_name: str = Field(min_length=1)
    patient_phone: str = Field(min_length=1)
    date: date
    time: time
    appointment_type: str = Field(min_length=1)
    notes: str | None = None

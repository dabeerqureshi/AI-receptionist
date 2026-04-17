from pydantic import BaseModel
from datetime import date
from typing import Optional


class AvailabilityRequest(BaseModel):
    date: date
    time: str


class BookingRequest(BaseModel):
    patient_name: str
    patient_phone: str
    date: date
    time: str

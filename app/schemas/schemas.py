from pydantic import BaseModel
from datetime import date
from typing import Optional


class AvailabilityRequest(BaseModel):
    tenant_id: str
    date: date
    time: str


class BookingRequest(BaseModel):
    tenant_id: str
    patient_name: str
    patient_phone: str
    date: date
    time: str

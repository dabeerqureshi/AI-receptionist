from pydantic import BaseModel
from datetime import date, time


class CheckAvailabilityRequest(BaseModel):
    date: date


class BookAppointmentRequest(BaseModel):
    patient_name: str
    patient_phone: str
<<<<<<< HEAD
    date: str
    time: str
=======
    date: date
    time: time
    appointment_type: str
>>>>>>> 83852af (Restore files from commit 2fc3762)
    notes: str | None = None

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from services import check_availability, book_appointment, get_available_slots

app = FastAPI(title="AI Receptionist", version="1.0")

class AvailabilityRequest(BaseModel):
    date: str
    reason: str

class BookingRequest(BaseModel):
    name: str
    phone: str
    date: str
    time: str
    reason: str

@app.get("/")
def root():
    return {"message": "AI Receptionist API"}

@app.post("/check-availability")
def check_date_availability(request: AvailabilityRequest):
    slots = get_available_slots(request.date, request.reason)
    return {
        "date": request.date,
        "reason": request.reason,
        "available_slots": slots
    }

@app.post("/book-appointment")
def create_booking(request: BookingRequest):
    result = book_appointment(
        name=request.name,
        phone=request.phone,
        date=request.date,
        time=request.time,
        reason=request.reason
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
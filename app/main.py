from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.database import Base, SessionLocal, engine
from app.db.models import Clinic
from app.routes import availability, booking

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Receptionist API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(availability.router)
app.include_router(booking.router)


@app.on_event("startup")
def startup():
    db = SessionLocal()
    try:
        clinic = db.query(Clinic).filter(Clinic.id == 1).first()
        if clinic is None:
            db.add(Clinic(id=1, name="Default Clinic"))
            db.commit()
    finally:
        db.close()


@app.get("/")
def root():
    return {
        "message": "AI Receptionist API Running",
        "endpoints": {
            "/api/v1/check-availability": "POST - Get available time slots",
            "/api/v1/book-appointment": "POST - Book an appointment",
            "/docs": "Interactive API Documentation"
        }
    }

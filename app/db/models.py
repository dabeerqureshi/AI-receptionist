from sqlalchemy import Column, Integer, String, Date, Time, DateTime
from app.db.database import Base
from datetime import datetime


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    patient_name = Column(String, index=True)
    patient_phone = Column(String, index=True)
    date = Column(Date, index=True)
    start_time = Column(Time)
    end_time = Column(Time)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class WorkingHours(Base):
    __tablename__ = "working_hours"

    id = Column(Integer, primary_key=True, index=True)
    day_of_week = Column(Integer, index=True)
    open_time = Column(Time)
    close_time = Column(Time)
    break_start = Column(Time, nullable=True)
    break_end = Column(Time, nullable=True)
    is_closed = Column(Integer, default=0)
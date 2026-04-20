from sqlalchemy import Column, Integer, String, Date, Time, ForeignKey, Enum, DateTime
from sqlalchemy.orm import relationship
from app.db.database import Base
import enum
from datetime import datetime


class AppointmentStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    phone = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    appointments = relationship("Appointment", back_populates="patient")


class AppointmentType(Base):
    __tablename__ = "appointment_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, unique=True)
    duration_minutes = Column(Integer, default=60)
    buffer_minutes = Column(Integer, default=5)


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    appointment_type_id = Column(Integer, ForeignKey("appointment_types.id"))
    date = Column(Date, index=True)
    start_time = Column(Time)
    end_time = Column(Time)
    status = Column(Enum(AppointmentStatus), default=AppointmentStatus.SCHEDULED)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="appointments")
    appointment_type = relationship("AppointmentType")


class WorkingHours(Base):
    __tablename__ = "working_hours"

    id = Column(Integer, primary_key=True, index=True)
    day_of_week = Column(Integer, index=True)
    open_time = Column(Time)
    close_time = Column(Time)
    is_closed = Column(Integer, default=0)


class Holiday(Base):
    __tablename__ = "holidays"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, index=True)
    reason = Column(String, nullable=True)

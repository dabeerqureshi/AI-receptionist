import enum
from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Enum, ForeignKey, Integer, String, Time, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.database import Base


class AppointmentStatus(str, enum.Enum):
    BOOKED = "booked"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"


class Clinic(Base):
    __tablename__ = "clinics"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    timezone = Column(String, default="America/Los_Angeles")
    default_duration_minutes = Column(Integer, default=60)
    default_buffer_minutes = Column(Integer, default=5)
    max_booking_days = Column(Integer, default=90)
    created_at = Column(DateTime, default=datetime.utcnow)


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True)
    response = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id"), index=True)
    name = Column(String, index=True)
    phone = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    appointments = relationship("Appointment", back_populates="patient")

    __table_args__ = (
        UniqueConstraint("clinic_id", "phone", name="_clinic_phone_uc"),
    )


class AppointmentType(Base):
    __tablename__ = "appointment_types"

    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id"), index=True)
    name = Column(String, index=True)
    duration_minutes = Column(Integer, default=60)
    buffer_minutes = Column(Integer, default=5)

    __table_args__ = (
        UniqueConstraint("clinic_id", "name", name="_clinic_name_uc"),
    )


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id"), index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    appointment_type_id = Column(Integer, ForeignKey("appointment_types.id"))
    date = Column(Date, index=True)
    start_time = Column(Time)
    end_time = Column(Time)
    status = Column(Enum(AppointmentStatus), default=AppointmentStatus.BOOKED)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="appointments")
    appointment_type = relationship("AppointmentType")

    __table_args__ = (
        UniqueConstraint("clinic_id", "date", "start_time", name="_clinic_date_time_uc"),
    )


class WorkingHours(Base):
    __tablename__ = "working_hours"

    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id"), index=True)
    day_of_week = Column(Integer, index=True)
    open_time = Column(Time)
    close_time = Column(Time)
    break_start = Column(Time, nullable=True)
    break_end = Column(Time, nullable=True)
    is_closed = Column(Integer, default=0)


class Holiday(Base):
    __tablename__ = "holidays"

    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id"), index=True)
    date = Column(Date, index=True)
    reason = Column(String, nullable=True)

    __table_args__ = (
        UniqueConstraint("clinic_id", "date", name="_clinic_date_uc"),
    )

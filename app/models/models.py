from sqlalchemy import Column, Integer, String, Time, Date, Boolean, UniqueConstraint
from app.db.database import Base
import enum


class AppointmentStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"


class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    timezone = Column(String, default="UTC")


class Doctor(Base):
    __tablename__ = "doctors"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, index=True)
    name = Column(String)


class WorkingHours(Base):
    __tablename__ = "working_hours"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, index=True)
    doctor_id = Column(Integer, index=True, nullable=True)
    day_of_week = Column(Integer)
    open_time = Column(Time)
    close_time = Column(Time)
    is_closed = Column(Boolean, default=False)


class Holiday(Base):
    __tablename__ = "holidays"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, index=True)
    date = Column(Date)
    reason = Column(String, nullable=True)


class Appointment(Base):
    __tablename__ = "appointments"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, index=True)
    doctor_id = Column(Integer, index=True)
    patient_name = Column(String)
    patient_phone = Column(String, nullable=True)
    date = Column(Date)
    time = Column(Time)
    status = Column(String, default=AppointmentStatus.SCHEDULED)
    notes = Column(String, nullable=True)
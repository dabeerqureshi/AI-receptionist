from sqlalchemy import create_engine, Column, Integer, String, Time, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

SQLALCHEMY_DATABASE_URL = "sqlite:///./ai_receptionist.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class Clinic(Base):
    __tablename__ = "clinics"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    api_key = Column(String, unique=True, index=True)

    settings = relationship("ClinicSettings", back_populates="clinic", uselist=False)
    working_hours = relationship("WorkingHours", back_populates="clinic")
    appointments = relationship("Appointment", back_populates="clinic")


class ClinicSettings(Base):
    __tablename__ = "clinic_settings"

    tenant_id = Column(String, ForeignKey("clinics.id"), primary_key=True)
    timezone = Column(String, default="UTC")
    appointment_duration = Column(Integer, default=30)

    clinic = relationship("Clinic", back_populates="settings")


class WorkingHours(Base):
    __tablename__ = "working_hours"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, ForeignKey("clinics.id"))
    day_of_week = Column(Integer)  # 0=Monday, 6=Sunday
    start_time = Column(Time)
    end_time = Column(Time)

    clinic = relationship("Clinic", back_populates="working_hours")


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, ForeignKey("clinics.id"))
    name = Column(String, index=True)
    phone = Column(String, index=True)
    date = Column(String)  # YYYY-MM-DD format
    time = Column(String)  # HH:MM format
    reason = Column(String)

    clinic = relationship("Clinic", back_populates="appointments")


# Create database tables
Base.metadata.create_all(bind=engine)

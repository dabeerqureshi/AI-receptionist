from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base, Clinic, ClinicSettings, WorkingHours
from datetime import time


def setup_sample_data():
    db = SessionLocal()

    # Clear existing data
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # Create Clinic A - Smile Dental
    clinic_a = Clinic(
        id="clinic_A",
        name="Smile Dental",
        api_key="abc123"
    )
    db.add(clinic_a)

    # Settings for Clinic A
    settings_a = ClinicSettings(
        tenant_id="clinic_A",
        timezone="Asia/Karachi",
        appointment_duration=30
    )
    db.add(settings_a)

    # Working hours for Clinic A
    working_hours_a = [
        WorkingHours(tenant_id="clinic_A", day_of_week=0, start_time=time(9, 0), end_time=time(17, 0)),  # Monday
        WorkingHours(tenant_id="clinic_A", day_of_week=1, start_time=time(10, 0), end_time=time(16, 0)),  # Tuesday
        WorkingHours(tenant_id="clinic_A", day_of_week=2, start_time=time(9, 0), end_time=time(17, 0)),  # Wednesday
        WorkingHours(tenant_id="clinic_A", day_of_week=3, start_time=time(9, 0), end_time=time(17, 0)),  # Thursday
        WorkingHours(tenant_id="clinic_A", day_of_week=4, start_time=time(9, 0), end_time=time(17, 0)),  # Friday
        WorkingHours(tenant_id="clinic_A", day_of_week=5, start_time=time(9, 0), end_time=time(13, 0)),  # Saturday
    ]
    db.add_all(working_hours_a)

    # Create Clinic B - Bright Care
    clinic_b = Clinic(
        id="clinic_B",
        name="Bright Care",
        api_key="xyz789"
    )
    db.add(clinic_b)

    # Settings for Clinic B
    settings_b = ClinicSettings(
        tenant_id="clinic_B",
        timezone="America/New_York",
        appointment_duration=60
    )
    db.add(settings_b)

    # Working hours for Clinic B
    working_hours_b = [
        WorkingHours(tenant_id="clinic_B", day_of_week=0, start_time=time(9, 0), end_time=time(17, 0)),  # Monday
        WorkingHours(tenant_id="clinic_B", day_of_week=1, start_time=time(9, 0), end_time=time(17, 0)),  # Tuesday
        WorkingHours(tenant_id="clinic_B", day_of_week=2, start_time=time(9, 0), end_time=time(17, 0)),  # Wednesday
        WorkingHours(tenant_id="clinic_B", day_of_week=3, start_time=time(9, 0), end_time=time(17, 0)),  # Thursday
        WorkingHours(tenant_id="clinic_B", day_of_week=4, start_time=time(9, 0), end_time=time(17, 0)),  # Friday
    ]
    db.add_all(working_hours_b)

    db.commit()
    db.close()

    print("✅ Sample data created successfully!")
    print("\n🏥 Clinic A: Smile Dental")
    print("   API Key: abc123")
    print("   Timezone: Asia/Karachi")
    print("   Appointment Duration: 30 minutes")
    print("\n🏥 Clinic B: Bright Care")
    print("   API Key: xyz789")
    print("   Timezone: America/New_York")
    print("   Appointment Duration: 60 minutes")


if __name__ == "__main__":
    setup_sample_data()
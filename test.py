from __future__ import annotations

import os
import tempfile
import logging
from datetime import date, timedelta

from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db.models import Appointment, AppointmentType, Clinic, Holiday, WorkingHours
from app.main import root
from app.routes.availability import check_availability
from app.routes.booking import book_appointment
from app.schemas.requests import BookAppointmentRequest, CheckAvailabilityRequest


logging.getLogger("app.services.booking_service").setLevel(logging.ERROR)


class TestHarness:
    def __init__(self):
        fd, path = tempfile.mkstemp(prefix="ai_receptionist_test_", suffix=".db")
        os.close(fd)
        self.db_path = path
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            connect_args={"check_same_thread": False},
        )
        self.session_local = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)

    def close(self):
        self.engine.dispose()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def reset_db(self):
        Base.metadata.drop_all(bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        with self.session_local() as db:
            db.add_all(
                [
                    Clinic(id=1, name="Default Clinic", max_booking_days=30),
                    Clinic(id=2, name="Second Clinic", max_booking_days=30),
                ]
            )
            db.commit()

    def seed_working_day(
        self,
        clinic_id: int,
        target_date: date,
        open_time: str = "09:00",
        close_time: str = "17:00",
        break_start: str | None = None,
        break_end: str | None = None,
        is_closed: int = 0,
    ):
        from datetime import time

        def parse_time(value: str | None):
            if value is None:
                return None
            hour, minute = map(int, value.split(":"))
            return time(hour, minute)

        with self.session_local() as db:
            db.add(
                WorkingHours(
                    clinic_id=clinic_id,
                    day_of_week=target_date.weekday(),
                    open_time=parse_time(open_time),
                    close_time=parse_time(close_time),
                    break_start=parse_time(break_start),
                    break_end=parse_time(break_end),
                    is_closed=is_closed,
                )
            )
            db.commit()

    def seed_appointment_type(self, clinic_id: int, name: str, duration_minutes: int, buffer_minutes: int):
        with self.session_local() as db:
            db.add(
                AppointmentType(
                    clinic_id=clinic_id,
                    name=name,
                    duration_minutes=duration_minutes,
                    buffer_minutes=buffer_minutes,
                )
            )
            db.commit()

    def seed_holiday(self, clinic_id: int, holiday_date: date, reason: str = "Closed"):
        with self.session_local() as db:
            db.add(Holiday(clinic_id=clinic_id, date=holiday_date, reason=reason))
            db.commit()

    def appointment_count(self, clinic_id: int):
        with self.session_local() as db:
            return db.query(Appointment).filter(Appointment.clinic_id == clinic_id).count()


def next_weekday(start: date, weekday: int):
    days_ahead = (weekday - start.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return start + timedelta(days=days_ahead)


def assert_true(condition: bool, message: str):
    if not condition:
        raise AssertionError(message)


def assert_equal(actual, expected, message: str):
    if actual != expected:
        raise AssertionError(f"{message}: expected {expected!r}, got {actual!r}")


def normalize_slots(slots):
    return [slot.strftime("%H:%M:%S") if hasattr(slot, "strftime") else str(slot) for slot in slots]


def test_root_endpoint(harness: TestHarness):
    payload = root()
    assert_true("AI Receptionist API Running" in payload["message"], "Root payload should expose service message")


def test_availability_returns_buffered_slots(harness: TestHarness):
    harness.reset_db()
    target_date = next_weekday(date.today(), 0)
    harness.seed_working_day(1, target_date)
    harness.seed_appointment_type(1, "cleaning", 60, 5)

    with harness.session_local() as db:
        response = check_availability(
            request=CheckAvailabilityRequest(date=target_date, appointment_type="cleaning"),
            db=db,
            clinic_id=1,
        )
    slots = normalize_slots(response["available_slots"])
    assert_equal(slots, ["09:00:00", "10:05:00", "11:10:00", "12:15:00", "13:20:00"], "Buffered slots should be returned")
    assert_equal(response["message"], "Available slots retrieved successfully", "Availability should return a success message when slots exist")


def test_booking_success_and_conflict(harness: TestHarness):
    harness.reset_db()
    target_date = next_weekday(date.today(), 1)
    harness.seed_working_day(1, target_date, break_start="12:00", break_end="13:00")
    harness.seed_appointment_type(1, "cleaning", 60, 5)

    with harness.session_local() as db:
        first = book_appointment(
            request=BookAppointmentRequest(
                patient_name="Alice",
                patient_phone="+15550000001",
                appointment_type="cleaning",
                date=target_date,
                time="09:00",
                notes="First visit",
            ),
            db=db,
            clinic_id=1,
        )
    assert_true(first["success"], "First booking should succeed")

    with harness.session_local() as db:
        second = book_appointment(
            request=BookAppointmentRequest(
                patient_name="Bob",
                patient_phone="+15550000002",
                appointment_type="cleaning",
                date=target_date,
                time="09:00",
                notes="Conflicting visit",
            ),
            db=db,
            clinic_id=1,
        )
    assert_true(not second["success"], "Conflicting booking should be rejected")
    assert_equal(harness.appointment_count(1), 1, "Only one appointment should exist after conflict test")


def test_buffered_follow_up_slot_books(harness: TestHarness):
    harness.reset_db()
    target_date = next_weekday(date.today(), 2)
    harness.seed_working_day(1, target_date)
    harness.seed_appointment_type(1, "cleaning", 60, 5)

    with harness.session_local() as db:
        first = book_appointment(
            request=BookAppointmentRequest(
                patient_name="Alice",
                patient_phone="+15550000003",
                appointment_type="cleaning",
                date=target_date,
                time="09:00",
                notes="Opening slot",
            ),
            db=db,
            clinic_id=1,
        )
    with harness.session_local() as db:
        second = book_appointment(
            request=BookAppointmentRequest(
                patient_name="Bob",
                patient_phone="+15550000004",
                appointment_type="cleaning",
                date=target_date,
                time="10:05",
                notes="Buffered slot",
            ),
            db=db,
            clinic_id=1,
        )

    assert_true(first["success"], "First buffered scenario booking should succeed")
    assert_true(second["success"], "Second buffered slot should succeed")
    assert_equal(harness.appointment_count(1), 2, "Two buffered appointments should be stored")


def test_lunch_break_is_not_offered(harness: TestHarness):
    harness.reset_db()
    target_date = next_weekday(date.today(), 3)
    harness.seed_working_day(1, target_date, break_start="12:00", break_end="13:00")
    harness.seed_appointment_type(1, "cleaning", 60, 0)

    with harness.session_local() as db:
        response = check_availability(
            request=CheckAvailabilityRequest(date=target_date, appointment_type="cleaning"),
            db=db,
            clinic_id=1,
        )
    slots = normalize_slots(response["available_slots"])
    assert_true("12:00:00" not in slots, "Lunch break slot should not be returned")


def test_holiday_blocks_availability_and_booking(harness: TestHarness):
    harness.reset_db()
    target_date = next_weekday(date.today(), 4)
    harness.seed_working_day(1, target_date)
    harness.seed_appointment_type(1, "cleaning", 60, 5)
    harness.seed_holiday(1, target_date, "Holiday")

    with harness.session_local() as db:
        availability = check_availability(
            request=CheckAvailabilityRequest(date=target_date, appointment_type="cleaning"),
            db=db,
            clinic_id=1,
        )
    with harness.session_local() as db:
        booking = book_appointment(
            request=BookAppointmentRequest(
                patient_name="Holiday Patient",
                patient_phone="+15550000005",
                appointment_type="cleaning",
                date=target_date,
                time="09:00",
                notes="Should fail",
            ),
            db=db,
            clinic_id=1,
        )

    assert_equal(availability["available_slots"], [], "Holiday should yield no availability")
    assert_true("Clinic is closed" in availability["message"], "Holiday availability should explain why the day is blocked")
    assert_true(not booking["success"], "Holiday booking should fail")
    assert_true("Clinic is closed" in booking["message"], "Holiday booking should return a clear reason")


def test_closed_day_blocks_availability(harness: TestHarness):
    harness.reset_db()
    target_date = next_weekday(date.today(), 6)
    harness.seed_working_day(1, target_date, is_closed=1)
    harness.seed_appointment_type(1, "cleaning", 60, 5)

    with harness.session_local() as db:
        response = check_availability(
            request=CheckAvailabilityRequest(date=target_date, appointment_type="cleaning"),
            db=db,
            clinic_id=1,
        )
    assert_equal(response["available_slots"], [], "Closed day should yield no availability")
    assert_true("Clinic is closed" in response["message"], "Closed day should explain why no slots are available")


def test_real_world_sunday_booking_is_rejected(harness: TestHarness):
    harness.reset_db()
    sunday_date = next_weekday(date.today(), 6)
    harness.seed_appointment_type(1, "consultation", 30, 10)

    with harness.session_local() as db:
        availability = check_availability(
            request=CheckAvailabilityRequest(date=sunday_date, appointment_type="consultation"),
            db=db,
            clinic_id=1,
        )
    with harness.session_local() as db:
        booking = book_appointment(
            request=BookAppointmentRequest(
                patient_name="Sunday Walk-in",
                patient_phone="+15550000009",
                appointment_type="consultation",
                date=sunday_date,
                time="10:00",
                notes="Requested on a Sunday",
            ),
            db=db,
            clinic_id=1,
        )

    assert_equal(availability["available_slots"], [], "Sunday should not expose available slots by default")
    assert_true("Clinic is closed" in availability["message"], "Sunday availability should explain closure")
    assert_true(not booking["success"], "Sunday booking should be rejected")
    assert_true("Clinic is closed" in booking["message"], "Sunday booking should explain closure")
    assert_equal(harness.appointment_count(1), 0, "Sunday booking should not create an appointment")


def test_past_and_future_booking_window(harness: TestHarness):
    harness.reset_db()
    past_date = date.today() - timedelta(days=1)
    future_date = date.today() + timedelta(days=31)

    with harness.session_local() as db:
        past_response = check_availability(
            request=CheckAvailabilityRequest(date=past_date, appointment_type="cleaning"),
            db=db,
            clinic_id=1,
        )
    with harness.session_local() as db:
        future_response = check_availability(
            request=CheckAvailabilityRequest(date=future_date, appointment_type="cleaning"),
            db=db,
            clinic_id=1,
        )

    assert_equal(past_response["available_slots"], [], "Past dates should not be bookable")
    assert_equal(future_response["available_slots"], [], "Dates beyond clinic booking window should not be bookable")
    assert_equal(past_response["message"], "Past dates cannot be booked", "Past-date availability should explain the restriction")
    assert_true("Bookings are only available through" in future_response["message"], "Future-date availability should explain the booking window")


def test_real_world_already_booked_appointment_is_rejected(harness: TestHarness):
    harness.reset_db()
    target_date = next_weekday(date.today(), 0)
    harness.seed_working_day(1, target_date)
    harness.seed_appointment_type(1, "follow-up", 45, 15)

    with harness.session_local() as db:
        first_booking = book_appointment(
            request=BookAppointmentRequest(
                patient_name="Maria Garcia",
                patient_phone="+15550000010",
                appointment_type="follow-up",
                date=target_date,
                time="09:00",
                notes="Existing confirmed appointment",
            ),
            db=db,
            clinic_id=1,
        )
    with harness.session_local() as db:
        second_booking = book_appointment(
            request=BookAppointmentRequest(
                patient_name="James Wilson",
                patient_phone="+15550000011",
                appointment_type="follow-up",
                date=target_date,
                time="09:00",
                notes="Tries to take an already booked slot",
            ),
            db=db,
            clinic_id=1,
        )

    assert_true(first_booking["success"], "Initial real-world booking should succeed")
    assert_true(not second_booking["success"], "Already booked appointment should be rejected")
    assert_equal(second_booking["message"], "This time slot is no longer available", "Conflict should return the expected message")
    assert_equal(harness.appointment_count(1), 1, "Only the original appointment should remain booked")


def test_clinic_isolation(harness: TestHarness):
    harness.reset_db()
    target_date = next_weekday(date.today(), 0)
    harness.seed_working_day(1, target_date)
    harness.seed_working_day(2, target_date)
    harness.seed_appointment_type(1, "cleaning", 60, 5)
    harness.seed_appointment_type(2, "cleaning", 60, 5)

    with harness.session_local() as db:
        clinic_one = book_appointment(
            request=BookAppointmentRequest(
                patient_name="Clinic One",
                patient_phone="+15550000006",
                appointment_type="cleaning",
                date=target_date,
                time="09:00",
                notes="Clinic one",
            ),
            db=db,
            clinic_id=1,
        )
    with harness.session_local() as db:
        clinic_two = book_appointment(
            request=BookAppointmentRequest(
                patient_name="Clinic Two",
                patient_phone="+15550000007",
                appointment_type="cleaning",
                date=target_date,
                time="09:00",
                notes="Clinic two",
            ),
            db=db,
            clinic_id=2,
        )

    assert_true(clinic_one["success"], "Clinic one booking should succeed")
    assert_true(clinic_two["success"], "Clinic two booking should succeed")
    assert_equal(harness.appointment_count(1), 1, "Clinic one should have one appointment")
    assert_equal(harness.appointment_count(2), 1, "Clinic two should have one appointment")


def test_idempotency_replays_same_response(harness: TestHarness):
    harness.reset_db()
    target_date = next_weekday(date.today(), 1)
    harness.seed_working_day(1, target_date)
    harness.seed_appointment_type(1, "cleaning", 60, 5)
    headers = {"X-Idempotency-Key": "booking-123"}
    payload = {
        "patient_name": "Idempotent Patient",
        "patient_phone": "+15550000008",
        "appointment_type": "cleaning",
        "date": target_date.isoformat(),
        "time": "09:00",
        "notes": "Should replay",
    }

    with harness.session_local() as db:
        first = book_appointment(
            request=BookAppointmentRequest(**payload),
            db=db,
            clinic_id=1,
            x_idempotency_key=headers["X-Idempotency-Key"],
        )
    with harness.session_local() as db:
        second = book_appointment(
            request=BookAppointmentRequest(**payload),
            db=db,
            clinic_id=1,
            x_idempotency_key=headers["X-Idempotency-Key"],
        )

    assert_equal(first, second, "Idempotent retries should replay the original response")
    assert_equal(harness.appointment_count(1), 1, "Idempotent retry should not create a second appointment")


def test_booking_past_date_returns_clear_message(harness: TestHarness):
    harness.reset_db()
    past_date = date.today() - timedelta(days=1)

    with harness.session_local() as db:
        response = book_appointment(
            request=BookAppointmentRequest(
                patient_name="Past Patient",
                patient_phone="+15550000012",
                appointment_type="cleaning",
                date=past_date,
                time="09:00",
                notes="Should fail",
            ),
            db=db,
            clinic_id=1,
        )

    assert_true(not response["success"], "Past-date booking should fail")
    assert_equal(response["message"], "Past dates cannot be booked", "Past-date booking should return a clear validation message")
    assert_equal(harness.appointment_count(1), 0, "Past-date booking should not create an appointment")


def test_request_validation_rejects_blank_fields(harness: TestHarness):
    try:
        BookAppointmentRequest(
            patient_name="",
            patient_phone="",
            appointment_type="",
            date=date.today(),
            time="09:00",
            notes=None,
        )
    except ValidationError:
        return

    raise AssertionError("Blank booking fields should be rejected by the request schema")


def main():
    harness = TestHarness()
    tests = [
        test_root_endpoint,
        test_availability_returns_buffered_slots,
        test_booking_success_and_conflict,
        test_buffered_follow_up_slot_books,
        test_lunch_break_is_not_offered,
        test_holiday_blocks_availability_and_booking,
        test_closed_day_blocks_availability,
        test_real_world_sunday_booking_is_rejected,
        test_past_and_future_booking_window,
        test_real_world_already_booked_appointment_is_rejected,
        test_clinic_isolation,
        test_idempotency_replays_same_response,
        test_booking_past_date_returns_clear_message,
        test_request_validation_rejects_blank_fields,
    ]

    try:
        for test_func in tests:
            test_func(harness)
            print(f"PASS {test_func.__name__}")
        print(f"PASS All {len(tests)} scenarios completed successfully")
    finally:
        harness.close()


if __name__ == "__main__":
    main()

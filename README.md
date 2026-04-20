# AI Receptionist

A focused appointment-booking backend with a lightweight operations dashboard. The repository contains a FastAPI API for scheduling and a Streamlit dashboard for viewing appointments.

## Stack

- FastAPI
- SQLAlchemy
- SQLite
- Pydantic
- Streamlit

## Project Structure

- `app/`: API, database models, routes, and services
- `dashboard.py`: Streamlit dashboard
- `test.py`: end-to-end booking test script
- `requirements.txt`: runtime and test dependencies

## Features

- Clinic-scoped booking with `clinic_id`
- Appointment-type duration and buffer handling
- Slot availability checks and final booking revalidation
- Idempotency support for retries
- Holiday, Sunday, and booking-window validation
- Dashboard search, filtering, and live refresh

## Setup

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Run the API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Available endpoints:

- `GET /`
- `POST /api/v1/check-availability?clinic_id=1`
- `POST /api/v1/book-appointment?clinic_id=1`
- `GET /docs`

## Run the Dashboard

```bash
streamlit run dashboard.py
```

## Example Payloads

Check availability:

```json
{
  "date": "2026-04-20",
  "appointment_type": "cleaning"
}
```

Book appointment:

```json
{
  "patient_name": "John Doe",
  "patient_phone": "+15551234567",
  "appointment_type": "cleaning",
  "date": "2026-04-20",
  "time": "10:00",
  "notes": "First visit"
}
```

## Testing

Start the API first, then run:

```bash
venv\Scripts\python.exe test.py
```

## Notes

- The default database is `receptionist.db`.
- `tzdata` is included for Windows timezone support.
- `aiohttp` is included because the repository ships with an async API test script.

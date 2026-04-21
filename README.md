# AI Receptionist

A multi-tenant appointment-booking backend with dedicated operations dashboards. This repository contains a FastAPI API for scheduling appointments, with tenant isolation via API keys, and separate Streamlit dashboards for tenants and administrators.

## Stack

- FastAPI
- SQLAlchemy ORM
- SQLite Database
- Pydantic Validation
- Streamlit (Tenant & Admin Dashboards)
- Multi-tenant architecture with API key authentication

## Project Structure

- `main.py`: FastAPI API server with all endpoints
- `database.py`: Database models and connection setup
- `services.py`: Core business logic for availability checking and booking
- `tenant_dashboard.py`: Clinic-specific dashboard for viewing appointments
- `admin_dashboard.py`: System-wide administrator dashboard
- `requirements.txt`: Runtime dependencies

## Features

- ✅ Multi-tenant isolation with API key authentication
- ✅ Clinic-specific working hours configuration
- ✅ Intelligent slot availability calculation
- ✅ Appointment booking with conflict detection
- ✅ Custom appointment duration support
- ✅ Timezone handling per clinic
- ✅ Separate tenant and admin dashboards
- ✅ Automatic OpenAPI documentation

## Setup

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Run the API Server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## API Authentication

All API endpoints (except root) require an `X-API-Key` header for tenant authentication.

## Available Endpoints

| Method | Endpoint                | Description                                      |
|--------|-------------------------|--------------------------------------------------|
| GET    | `/`                     | API status check                                 |
| POST   | `/check-availability`   | Get available time slots for a specific date     |
| POST   | `/book-appointment`     | Book a new appointment                           |
| GET    | `/clinic/settings`      | Retrieve clinic configuration and working hours  |
| GET    | `/docs`                 | Interactive OpenAPI documentation                |
| GET    | `/redoc`                | Alternative API documentation                     |

### Check Availability
**POST** `/check-availability`

Headers:
```
X-API-Key: your-clinic-api-key
Content-Type: application/json
```

Request Body:
```json
{
  "date": "2026-04-22"
}
```

Response:
```json
{
  "tenant_id": 1,
  "clinic_name": "Example Clinic",
  "date": "2026-04-22",
  "available_slots": ["09:00", "09:30", "10:00", "10:30"]
}
```

### Book Appointment
**POST** `/book-appointment`

Headers:
```
X-API-Key: your-clinic-api-key
Content-Type: application/json
```

Request Body:
```json
{
  "name": "Patient Full Name",
  "phone": "+15551234567",
  "date": "2026-04-22",
  "time": "10:00",
  "reason": "Appointment description / notes"
}
```

Success Response:
```json
{
  "success": true,
  "message": "Appointment booked successfully",
  "appointment_id": 42
}
```

### Get Clinic Settings
**GET** `/clinic/settings`

Headers:
```
X-API-Key: your-clinic-api-key
```

Returns clinic profile, timezone, appointment duration, and configured working hours.

## Run Dashboards

### Tenant Dashboard (Clinic View)
```bash
streamlit run tenant_dashboard.py
```

### Admin Dashboard (System View)
```bash
streamlit run admin_dashboard.py
```

## Notes

- Default database file: `receptionist.db` (auto-created on first run)
- Windows timezone support included via `tzdata`
- API documentation is available at `http://localhost:8000/docs` when server is running
- Each clinic/tenant gets a dedicated API key for authentication
- Appointments are fully isolated between tenants
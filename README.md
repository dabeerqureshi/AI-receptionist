# AI Receptionist

A complete multi-tenant appointment booking system with dedicated dashboards. Enterprise-grade FastAPI backend with tenant isolation, API key authentication, and separate Streamlit dashboards for clinics and system administrators.

## Stack

- **Backend**: FastAPI + Pydantic Validation
- **Database**: SQLite with SQLAlchemy ORM
- **Dashboards**: Streamlit (Tenant & Admin)
- **Authentication**: API Keys + JWT for Admin
- **Architecture**: Multi-tenant isolation
- **Timezone Support**: Full timezone handling per clinic

## Project Structure

| File | Description |
|---|---|
| `main.py` | FastAPI API Server with all endpoints |
| `database.py` | Database models, migrations and connection |
| `services.py` | Core business logic, availability calculation |
| `api_client.py` | Official Python API Client Library |
| `tenant_dashboard.py` | Clinic dashboard for appointment management |
| `admin_dashboard.py` | System administrator dashboard |
| `dashboard_backend.py` | Dashboard backend services |
| `requirements.txt` | Project dependencies |

## Features

✅ **Multi-tenant architecture with full isolation**
✅ Per-clinic API key authentication
✅ Configurable working hours per tenant
✅ Intelligent slot availability calculation
✅ Conflict detection for double bookings
✅ Custom appointment duration support
✅ Full timezone handling per clinic
✅ Appointment CRUD operations
✅ Admin system management dashboard
✅ Clinic management interface
✅ API key rotation & security
✅ System health monitoring
✅ OpenAPI interactive documentation
✅ Complete REST API client library

## Setup

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### First Run
The system will automatically initialize the database on first startup. Default administrator account is created:
- **Username**: `admin`
- **Password**: `admin123`

> ❗ Change default admin password immediately after first login

## Run the API Server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API Documentation will be available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Run Dashboards

### Tenant Dashboard (Clinic View)
For clinic staff to manage appointments:
```bash
streamlit run tenant_dashboard.py
```

### Admin Dashboard (System View)
For system administrators to manage clinics:
```bash
streamlit run admin_dashboard.py
```

## API Authentication

| Endpoint Type | Authentication |
|---|---|
| Tenant Endpoints | `X-API-Key` Header |
| Admin Endpoints | `Authorization: Bearer <token>` |

## Complete API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | API health check |
| | **Tenant API** | |
| `POST` | `/tenant/auth/verify` | Verify clinic credentials |
| `GET` | `/tenant/clinic` | Get clinic profile |
| `GET` | `/clinic/settings` | Get clinic settings |
| `GET` | `/tenant/appointments` | List all appointments |
| `GET` | `/tenant/appointments/{id}` | Get single appointment |
| `POST` | `/tenant/appointments` | Create new appointment |
| `PUT` | `/tenant/appointments/{id}` | Update appointment |
| `DELETE` | `/tenant/appointments/{id}` | Cancel appointment |
| `PUT` | `/tenant/working-hours` | Update working hours |
| `PUT` | `/tenant/settings` | Update clinic settings |
| `POST` | `/check-availability` | Check available slots |
| `POST` | `/book-appointment` | Public booking endpoint |
| | **Admin API** | |
| `POST` | `/admin/auth/login` | Admin login |
| `GET` | `/admin/summary` | System summary statistics |
| `GET` | `/admin/clinics` | List all clinics |
| `POST` | `/admin/clinics` | Create new clinic |
| `DELETE` | `/admin/clinics/{id}` | Delete clinic |
| `POST` | `/admin/clinics/{id}/rotate-api-key` | Rotate clinic API key |
| `PUT` | `/admin/clinics/{id}/working-hours` | Update clinic working hours |
| `GET` | `/admin/appointments` | List all system appointments |
| `DELETE` | `/admin/appointments` | Clear all appointments |
| `GET` | `/admin/system/health` | System health status |
| `DELETE` | `/admin/system/data` | Reset all system data |

## Using the API Client

Import the official client from `api_client.py`:

```python
from api_client import *

# Tenant API Example
api_key = "your-clinic-api-key"

# Check available slots
slots = api_request("POST", "/check-availability",
    payload={"date": "2026-04-25"},
    api_key=api_key
)

# Create appointment
tenant_create_appointment(
    api_key=api_key,
    name="John Doe",
    phone="+15551234567",
    appointment_date="2026-04-25",
    appointment_time="10:00",
    reason="General checkup"
)


## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `API_BASE_URL` | `http://localhost:8000` | API Server base URL |
| `DATABASE_URL` | `sqlite:///./receptionist.db` | Database connection string |
| `ADMIN_PASSWORD` | `` | Default admin password |
| `SECRET_KEY` | Auto-generated | JWT signing secret |

## Troubleshooting

❌ **"Could not reach API"**: Ensure FastAPI server is running on port 8000
❌ **"Invalid API Key"**: Verify X-API-Key header is correctly set
❌ **Timezone issues**: Install `tzdata` package for Windows timezone support
❌ **Database locked**: Only one process may write to SQLite database at a time

## Data Storage

- Default database file: `receptionist.db` (auto created)
- All appointments are isolated per tenant
- Full audit trail of all operations
- No external dependencies required

## Development

```bash
# Run full test suite
pytest

# Check code style
flake8

# Format code
black *.py
```

## Notes

- Each clinic receives a unique API key
- API keys should be kept secure
- Default admin credentials should be changed
- All endpoints are rate limited
- HTTPS is recommended for production deployments
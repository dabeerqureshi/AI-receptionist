# AI Receptionist Booking API

Production-ready multi-tenant appointment booking system for clinics, designed for Vapi voice AI integration.

## ✨ Features

- ✅ **Multi-tenancy** - Full tenant isolation with secure JWT authentication
- ✅ **Smart Availability** - 30-minute slot generation with working hours and holiday support
- ✅ **Booking Management** - Book, cancel, reschedule appointments
- ✅ **Timezone Support** - Per-tenant timezone handling (store UTC, display local)
- ✅ **Vapi Compatible** - Simple JSON APIs ready for Vapi tool calls
- ✅ **Clean Architecture** - Service layer pattern, proper separation of concerns
- ✅ **Production Ready** - Logging, error handling, input validation

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Server
```bash
uvicorn app.main:app --reload
```

### 3. Access API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 📋 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/login` | Get JWT token (demo: demo/demo) |
| POST | `/check-availability` | Check available slots for doctor + date |
| POST | `/suggest-slot` | Get earliest available slot |
| POST | `/book-appointment` | Create new appointment |
| POST | `/cancel/{id}` | Cancel appointment |
| POST | `/reschedule/{id}` | Reschedule appointment |
| GET | `/appointments` | Get all appointments for tenant |

## 🏗️ Architecture

```
app/
├── main.py                 # FastAPI application entry
├── db/
│   └── database.py         # DB configuration & session management
├── models/
│   └── models.py           # SQLAlchemy ORM models
├── schemas/
│   └── schemas.py          # Pydantic validation schemas
├── services/
│   ├── auth_service.py     # JWT authentication
│   ├── availability_service.py  # Slot generation logic
│   └── booking_service.py  # Appointment business logic
└── api/
    └── routes.py           # API route definitions
```

## 🔐 Authentication

All endpoints (except /auth/login and /health) require JWT token in Authorization header:
```
Authorization: Bearer <your-token>
```

Token contains `tenant_id` which is automatically injected into all operations. Tenant ID is NEVER accepted from request body.

## 🔧 Configuration

Edit `.env` file for environment variables:
- `DATABASE_URL` - Database connection string
- `JWT_SECRET_KEY` - Secret for signing tokens
- `JWT_EXPIRE_MINUTES` - Token expiration time

## 🎯 Vapi Integration

This API is designed to be directly used as Vapi tools. All endpoints accept simple JSON inputs and return clean flat responses that voice AI can easily parse.

Example Vapi tool configuration:
```json
{
  "name": "check_availability",
  "description": "Check available appointment slots",
  "parameters": {
    "doctor_id": "number",
    "date": "YYYY-MM-DD"
  }
}
```

## 📊 Database Models

- **Tenant** - Clinic/organization with timezone
- **Doctor** - Doctors per clinic
- **Appointment** - Patient appointments
- **WorkingHours** - Clinic and doctor specific hours
- **Holiday** - Clinic closed dates

## 🧪 Testing

Use the interactive Swagger UI at `/docs` to test all endpoints.

1. First login with `demo` / `demo` to get your token
2. Click "Authorize" button and enter the token
3. Test all endpoints

## 📝 License

Production ready for clinic AI receptionist systems.
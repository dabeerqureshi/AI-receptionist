# AI Dental Receptionist - Phase 1 Backend MVP

SaaS Backend for AI Dental Receptionist system. This is the core scheduling engine that will integrate with VAPI voice AI.

---

## 🎯 Phase 1 Status: ✅ COMPLETE

## 🏗️ Architecture

```
VAPI (Future)
    ↓
Backend API
    ↓
Scheduling Engine
    ↓
Fake PMS Database
```

---

## 🚀 Features Implemented

### ✅ 1. Availability API
**Endpoint:** `POST /api/v1/check-availability`

**Input:**
```json
{
  "tenant_id": 1,
  "date": "2026-04-20",
  "appointment_type": "cleaning"
}
```

**Output:**
- Returns 3-5 best available slots
- Intelligently distributed across the day
- Human readable 12 hour format

### ✅ 2. Booking API
**Endpoint:** `POST /api/v1/book-appointment`

**Input:**
```json
{
  "tenant_id": 1,
  "patient_name": "John Doe",
  "patient_phone": "+15551234567",
  "appointment_type": "cleaning",
  "date": "2026-04-20",
  "time": "10:00",
  "notes": "First visit"
}
```

**Output:** Booking confirmation with unique appointment ID

---

### ✅ 3. Scheduling Engine
| Feature | Status |
|---------|--------|
| Working Hours 9AM - 5PM | ✅ |
| Sunday Closed | ✅ |
| Appointment duration support | ✅ |
| 5 minute buffer time | ✅ |
| Holiday exclusion | ✅ |
| 100% Double booking prevention | ✅ |
| Atomic database locking | ✅ |
| Race condition protection | ✅ |

---

### ✅ Supported Appointment Types
| Type | Duration | Buffer | Total Slot |
|------|----------|--------|------------|
| Cleaning | 45 min | 5 min | 50 min |
| Emergency | 30 min | 5 min | 35 min |
| Checkup | 30 min | 5 min | 35 min |
| Filling | 60 min | 10 min | 70 min |

---

## 📦 Database Entities
- Clinics (Tenants)
- Patients
- Appointments
- Appointment Types
- Working Hours
- Holidays

---

## 🔧 Tech Stack
- FastAPI
- SQLite (Postgres ready)
- SQLAlchemy ORM
- Pydantic schemas

---

## 🚀 Run Server

```bash
pip install -r requirements.txt
python app/main.py
```

API will be running at: `http://localhost:8000`

Swagger Docs: `http://localhost:8000/docs`

---

## ⚠️ Phase 1 Exclusions
❌ No Open Dental integration
❌ No VAPI integration
❌ No payment system
❌ No insurance logic
❌ No rescheduling system

---

## 📬 Postman Collection
Import `AI-Receptionist-API.postman_collection.json` for ready to use API requests.
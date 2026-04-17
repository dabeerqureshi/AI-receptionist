# AI Receptionist Booking API

✅ Production ready multi-tenant appointment booking system for clinics, Vapi compatible.

## ✅ Features

| Feature | Status |
|---|---|
| Multi-Tenant SaaS | ✅ |
| API Key Authentication | ✅ |
| 60 Minute Appointments | ✅ |
| Working Hours 8AM - 5PM | ✅ |
| Sunday Closed | ✅ |
| Double Booking Protection | ✅ |
| Vapi Ready Endpoints | ✅ |
| Request Logging | ✅ |

---

## 🚀 Quick Start

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

✅ Server running at: http://localhost:8000
✅ API Documentation: http://localhost:8000/docs

---

## 📋 API Endpoints

### 🔑 Authentication
Add header to all requests:
```
X-API-Key: demo-clinic-key-123
```

### ✅ Check Availability
```http
POST /check-availability
Content-Type: application/json

{
  "date": "2026-04-25",
  "time": "09:00"
}
```

Response:
```json
{
  "available": true,
  "message": "Slot is available"
}
```

### ✅ Book Appointment
```http
POST /book-appointment
Content-Type: application/json

{
  "patient_name": "John Smith",
  "patient_phone": "+1234567890",
  "date": "2026-04-25",
  "time": "09:00"
}
```

Response:
```json
{
  "success": true,
  "appointment_id": 1,
  "message": "Appointment booked successfully"
}
```

---

## 🏢 Multi-Tenant SaaS

Add new clinics in `.env` file:
```
CLINIC_4_KEY=your-new-clinic-secret-key
```

Each clinic gets their own API key. All data is 100% isolated.

---

## 🎯 Vapi Integration

Add this header in your Vapi tool configuration:
```
Header Name: X-API-Key
Header Value: their-api-key
```

Endpoints are designed specifically for Vapi voice AI. No extra setup required.

---

## ⚙️ Configuration

Edit `.env` file:
```
DATABASE_URL=sqlite:///./receptionist.db
CLINIC_1_KEY=demo-clinic-key-123
CLINIC_2_KEY=clinic-key-456
CLINIC_3_KEY=clinic-key-789
```

---

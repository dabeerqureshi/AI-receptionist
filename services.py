from typing import List, Dict

# In-memory storage for bookings
booked_appointments = []

def get_available_slots(date: str, reason: str) -> List[str]:
    """Get all available time slots for given date"""
    all_slots = [
        "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
        "12:00", "14:00", "14:30", "15:00", "15:30", "16:00", "16:30", "17:00"
    ]
    
    # Filter out already booked slots for this date
    booked_times = [booking["time"] for booking in booked_appointments 
                   if booking["date"] == date]
    
    available = [slot for slot in all_slots if slot not in booked_times]
    return available

def check_availability(date: str, time: str) -> bool:
    """Check if specific date and time slot is available"""
    for booking in booked_appointments:
        if booking["date"] == date and booking["time"] == time:
            return False
    return True

def book_appointment(name: str, phone: str, date: str, time: str, reason: str) -> Dict:
    """Book an appointment after checking availability"""
    
    # Check if slot is already booked
    if not check_availability(date, time):
        return {
            "success": False,
            "message": f"Slot {time} on {date} is already booked. Please choose another time."
        }
    
    # Create new booking
    booking = {
        "name": name,
        "phone": phone,
        "date": date,
        "time": time,
        "reason": reason
    }
    
    booked_appointments.append(booking)
    
    return {
        "success": True,
        "message": "Appointment booked successfully",
        "booking_details": booking
    }
import streamlit as st
import pandas as pd
from datetime import datetime, time
from sqlalchemy.orm import Session
from database import SessionLocal, Clinic, ClinicSettings, WorkingHours, Appointment
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Page config
st.set_page_config(
    page_title="Clinic Dashboard | AI Receptionist",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Database connection
@st.cache_resource
def get_db_session():
    return SessionLocal()

db = get_db_session()

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'tenant_id' not in st.session_state:
    st.session_state.tenant_id = None
if 'clinic_name' not in st.session_state:
    st.session_state.clinic_name = None


# Authentication functions
def verify_tenant_credentials(clinic_id: str, api_key: str):
    """Verify tenant credentials against database"""
    clinic = db.query(Clinic).filter(Clinic.id == clinic_id, Clinic.api_key == api_key).first()
    if clinic:
        return True, clinic.name
    return False, None


# Authentication Check
if not st.session_state.authenticated:
    st.title("🔒 Clinic Login")
    
    with st.form("login_form", clear_on_submit=False):
        clinic_id = st.text_input("Clinic ID", help="Your unique clinic ID provided by admin")
        api_key = st.text_input("API Key", type="password", help="Your clinic API key")
        submitted = st.form_submit_button("Login", use_container_width=True)
        
        if submitted:
            if not clinic_id or not api_key:
                st.error("Please enter both Clinic ID and API Key")
            else:
                auth_success, clinic_name = verify_tenant_credentials(clinic_id, api_key)
                if auth_success:
                    st.session_state.authenticated = True
                    st.session_state.tenant_id = clinic_id
                    st.session_state.clinic_name = clinic_name
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid Clinic ID or API Key")
    
    st.info("💡 If you don't have credentials, please contact your system administrator")
    st.stop()


# Sidebar
st.sidebar.title(f"🏥 {st.session_state.clinic_name}")
st.sidebar.success("Logged in successfully")

if st.sidebar.button("🚪 Logout", use_container_width=True):
    st.session_state.authenticated = False
    st.session_state.tenant_id = None
    st.session_state.clinic_name = None
    st.rerun()

menu = st.sidebar.radio("Navigation", [
    "📊 Dashboard",
    "📅 Appointments",
    "⏰ Working Hours",
    "⚙️ Settings"
])


# Helper functions (tenant filtered - ONLY returns data for logged in tenant)
def get_my_appointments():
    return db.query(Appointment).filter(Appointment.tenant_id == st.session_state.tenant_id).all()

def get_my_settings():
    return db.query(ClinicSettings).filter(ClinicSettings.tenant_id == st.session_state.tenant_id).first()

def get_my_working_hours():
    return db.query(WorkingHours).filter(WorkingHours.tenant_id == st.session_state.tenant_id).all()


# --------------------
# DASHBOARD PAGE
# --------------------
if menu == "📊 Dashboard":
    st.title("📊 Clinic Dashboard")
    
    appointments = get_my_appointments()
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Metrics Cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Appointments", len(appointments))
    
    with col2:
        today_appointments = len([a for a in appointments if a.date == today])
        st.metric("Today's Appointments", today_appointments)
    
    with col3:
        future_appointments = len([a for a in appointments if a.date >= today])
        st.metric("Upcoming Appointments", future_appointments)
    
    with col4:
        settings = get_my_settings()
        st.metric("Appointment Duration", f"{settings.appointment_duration if settings else 30} min")
    
    st.divider()
    
    # Today's Appointments
    st.subheader("📅 Today's Appointments")
    today_appointments_list = [a for a in appointments if a.date == today]
    
    if today_appointments_list:
        df = pd.DataFrame([{
            "ID": a.id,
            "Patient Name": a.name,
            "Phone": a.phone,
            "Time": a.time,
            "Reason": a.reason
        } for a in today_appointments_list])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No appointments scheduled for today")
    
    st.divider()
    
    # Recent Appointments
    st.subheader("📋 Last 10 Appointments")
    if appointments:
        df = pd.DataFrame([{
            "ID": a.id,
            "Patient Name": a.name,
            "Phone": a.phone,
            "Date": a.date,
            "Time": a.time,
            "Reason": a.reason
        } for a in appointments[-10:]])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No appointments booked yet")


# --------------------
# APPOINTMENTS PAGE
# --------------------
elif menu == "📅 Appointments":
    st.title("📅 Appointments Management")
    
    appointments = get_my_appointments()
    
    # Add New Appointment
    with st.expander("➕ Add New Appointment", expanded=False):
        with st.form("new_appointment_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                patient_name = st.text_input("Patient Name")
                phone = st.text_input("Phone Number")
                app_date = st.date_input("Appointment Date")
            
            with col2:
                app_time = st.time_input("Appointment Time")
                reason = st.text_area("Reason for Visit")
            
            submitted = st.form_submit_button("Create Appointment")
            
            if submitted and patient_name and phone:
                new_appointment = Appointment(
                    tenant_id=st.session_state.tenant_id,
                    name=patient_name,
                    phone=phone,
                    date=str(app_date),
                    time=str(app_time)[:5],
                    reason=reason
                )
                db.add(new_appointment)
                db.commit()
                st.success("✅ Appointment created successfully!")
                st.rerun()
    
    st.divider()
    
    # View & Manage Appointments
    st.subheader("All Appointments")
    
    if appointments:
        # Create dataframe
        df = pd.DataFrame([{
            "ID": a.id,
            "Patient Name": a.name,
            "Phone": a.phone,
            "Date": a.date,
            "Time": a.time,
            "Reason": a.reason
        } for a in appointments])
        
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        st.divider()
        
        # Edit / Delete Appointment
        st.subheader("✏️ Edit / Cancel Appointment")
        
        appointment_ids = [a.id for a in appointments]
        selected_id = st.selectbox("Select Appointment", options=appointment_ids, format_func=lambda x: f"Appointment #{x}")
        
        if selected_id:
            appointment = db.query(Appointment).get(selected_id)
            
            if appointment and appointment.tenant_id == st.session_state.tenant_id:
                with st.form("edit_appointment_form"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        edit_name = st.text_input("Patient Name", value=appointment.name)
                        edit_phone = st.text_input("Phone Number", value=appointment.phone)
                        edit_date = st.text_input("Date", value=appointment.date)
                    
                    with col2:
                        edit_time = st.text_input("Time", value=appointment.time)
                        edit_reason = st.text_area("Reason for Visit", value=appointment.reason)
                    
                    col_update, col_delete = st.columns(2)
                    
                    with col_update:
                        update_btn = st.form_submit_button("💾 Update Appointment", use_container_width=True)
                    
                    with col_delete:
                        delete_btn = st.form_submit_button("🗑️ Cancel Appointment", type="primary", use_container_width=True)
                    
                    if update_btn:
                        appointment.name = edit_name
                        appointment.phone = edit_phone
                        appointment.date = edit_date
                        appointment.time = edit_time
                        appointment.reason = edit_reason
                        db.commit()
                        st.success("✅ Appointment updated successfully!")
                        st.rerun()
                    
                    if delete_btn:
                        db.delete(appointment)
                        db.commit()
                        st.success("✅ Appointment cancelled successfully!")
                        st.rerun()
    else:
        st.info("No appointments found")


# --------------------
# WORKING HOURS PAGE
# --------------------
elif menu == "⏰ Working Hours":
    st.title("⏰ Working Hours Configuration")
    
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    current_hours = get_my_working_hours()
    hours_map = {wh.day_of_week: wh for wh in current_hours}
    
    st.subheader("Edit Working Hours")
    updated_hours = []
    
    for day_num, day_name in enumerate(days):
        col1, col2, col3 = st.columns([2, 3, 3])
        
        with col1:
            enabled = st.checkbox(day_name, value=day_num in hours_map, key=f"enable_{day_num}")
        
        with col2:
            start_val = hours_map[day_num].start_time if day_num in hours_map else time(9,0)
            start_time = st.time_input("Start", value=start_val, key=f"start_{day_num}", disabled=not enabled)
        
        with col3:
            end_val = hours_map[day_num].end_time if day_num in hours_map else time(17,0)
            end_time = st.time_input("End", value=end_val, key=f"end_{day_num}", disabled=not enabled)
        
        if enabled:
            updated_hours.append((day_num, start_time, end_time))
    
    if st.button("💾 Save Working Hours", use_container_width=True):
        # Delete existing hours for this tenant
        db.query(WorkingHours).filter(WorkingHours.tenant_id == st.session_state.tenant_id).delete()
        
        # Add updated hours
        for day_num, start, end in updated_hours:
            db.add(WorkingHours(
                tenant_id=st.session_state.tenant_id,
                day_of_week=day_num,
                start_time=start,
                end_time=end
            ))
        
        db.commit()
        st.success("✅ Working hours saved successfully!")
        st.rerun()


# --------------------
# SETTINGS PAGE
# --------------------
elif menu == "⚙️ Settings":
    st.title("⚙️ Clinic Settings")
    
    settings = get_my_settings()
    clinic = db.query(Clinic).get(st.session_state.tenant_id)
    
    st.subheader("Clinic Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.text_input("Clinic ID", value=clinic.id, disabled=True)
        st.text_input("Clinic Name", value=clinic.name, disabled=True)
    
    with col2:
        st.text_input("API Key", value=clinic.api_key, type="password", disabled=True)
        st.text_input("Timezone", value=settings.timezone if settings else "UTC", disabled=True)
    
    st.divider()
    
    st.subheader("Appointment Settings")
    duration = st.number_input("Default Appointment Duration (minutes)", 
                              min_value=15, max_value=120, 
                              value=settings.appointment_duration if settings else 30,
                              step=15)
    
    if st.button("💾 Save Settings", use_container_width=True):
        if settings:
            settings.appointment_duration = duration
            db.commit()
            st.success("✅ Settings updated successfully!")
            st.rerun()


# Footer
st.sidebar.divider()
st.sidebar.caption("AI Receptionist Tenant Dashboard")
st.sidebar.caption(f"Tenant ID: {st.session_state.tenant_id}")
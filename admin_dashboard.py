import streamlit as st
import pandas as pd
from datetime import time
from sqlalchemy.orm import Session
from database import SessionLocal, Clinic, ClinicSettings, WorkingHours, Appointment
import uuid
import os
import hashlib
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Security functions
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Admin credentials loaded from environment variables
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH")

# Validate required environment variables
if not ADMIN_USERNAME or not ADMIN_PASSWORD_HASH:
    st.error("⚠️ Admin credentials not configured! Please set ADMIN_USERNAME and ADMIN_PASSWORD_HASH in .env file")
    st.stop()

def check_credentials(username, password):
    return username == ADMIN_USERNAME and hash_password(password) == ADMIN_PASSWORD_HASH

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# Page config
st.set_page_config(
    page_title="AI Receptionist Admin Dashboard",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Database connection
@st.cache_resource
def get_db_session():
    return SessionLocal()

db = get_db_session()

# Helper functions
def generate_api_key():
    return str(uuid.uuid4()).replace("-", "")[:12]

def get_all_clinics():
    return db.query(Clinic).all()

def get_clinic_settings(clinic_id):
    return db.query(ClinicSettings).filter(ClinicSettings.tenant_id == clinic_id).first()

def get_clinic_working_hours(clinic_id):
    return db.query(WorkingHours).filter(WorkingHours.tenant_id == clinic_id).all()

def get_all_appointments():
    return db.query(Appointment).all()

def delete_clinic(clinic_id):
    # Delete related records first
    db.query(WorkingHours).filter(WorkingHours.tenant_id == clinic_id).delete()
    db.query(ClinicSettings).filter(ClinicSettings.tenant_id == clinic_id).delete()
    db.query(Appointment).filter(Appointment.tenant_id == clinic_id).delete()
    db.query(Clinic).filter(Clinic.id == clinic_id).delete()
    db.commit()

# Authentication Check
if not st.session_state.authenticated:
    st.title("🔒 Admin Login")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        
        if submitted:
            if check_credentials(username, password):
                st.session_state.authenticated = True
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid username or password")
    
    st.stop()

# Logout button
if st.sidebar.button("🚪 Logout"):
    st.session_state.authenticated = False
    st.rerun()

# Sidebar navigation
st.sidebar.title("🏥 Admin Dashboard")
st.sidebar.success(f"Logged in as: {ADMIN_USERNAME}")
menu = st.sidebar.radio("Navigation", ["Dashboard", "Clinics Management", "Working Hours", "Appointments", "System"])

if menu == "Dashboard":
    st.title("📊 Admin Dashboard")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_clinics = db.query(Clinic).count()
        st.metric("Total Clinics", total_clinics)
    
    with col2:
        total_appointments = db.query(Appointment).count()
        st.metric("Total Appointments", total_appointments)
    
    with col3:
        total_working_hours = db.query(WorkingHours).count()
        st.metric("Working Hours Configured", total_working_hours)
    
    with col4:
        api_endpoint = "http://localhost:8000"
        st.metric("API Status", "Online")
    
    st.subheader("Recent Appointments")
    appointments = get_all_appointments()
    if appointments:
        df = pd.DataFrame([{
            "Clinic": db.query(Clinic).get(a.tenant_id).name,
            "Patient Name": a.name,
            "Phone": a.phone,
            "Date": a.date,
            "Time": a.time,
            "Reason": a.reason
        } for a in appointments[-10:]])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No appointments yet")

elif menu == "Clinics Management":
    st.title("🏥 Clinics Management")
    
    # Add new clinic form
    with st.expander("➕ Add New Clinic", expanded=False):
        with st.form("add_clinic_form"):
            clinic_name = st.text_input("Clinic Name")
            timezone = st.selectbox("Timezone", [
                "Asia/Karachi", "America/New_York", "Europe/London", 
                "Asia/Dubai", "Asia/Singapore", "UTC"
            ])
            appointment_duration = st.number_input("Default Appointment Duration (minutes)", min_value=15, max_value=120, value=30, step=15)
            
            submitted = st.form_submit_button("Create Clinic")
            if submitted and clinic_name:
                clinic_id = f"clinic_{str(uuid.uuid4())[:8]}"
                api_key = generate_api_key()
                
                new_clinic = Clinic(id=clinic_id, name=clinic_name, api_key=api_key)
                db.add(new_clinic)
                
                new_settings = ClinicSettings(
                    tenant_id=clinic_id,
                    timezone=timezone,
                    appointment_duration=appointment_duration
                )
                db.add(new_settings)
                
                # Add default working hours
                default_hours = []
                for day in range(5): # Mon-Fri
                    default_hours.append(WorkingHours(
                        tenant_id=clinic_id,
                        day_of_week=day,
                        start_time=time(9,0),
                        end_time=time(17,0)
                    ))
                db.add_all(default_hours)
                
                db.commit()
                st.success(f"✅ Clinic created successfully! API Key: `{api_key}`")
                st.balloons()
    
    # List existing clinics
    st.subheader("Existing Clinics")
    clinics = get_all_clinics()
    
    if clinics:
        for clinic in clinics:
            settings = get_clinic_settings(clinic.id)
            with st.expander(f"🏥 {clinic.name} (ID: {clinic.id})", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.text_input("Clinic Name", value=clinic.name, key=f"name_{clinic.id}", disabled=True)
                    st.text_input("API Key", value=clinic.api_key, key=f"api_{clinic.id}", type="password")
                    st.text_input("Timezone", value=settings.timezone if settings else "UTC", disabled=True)
                
                with col2:
                    st.text_input("Appointment Duration", value=f"{settings.appointment_duration if settings else 30} minutes", disabled=True)
                    working_hours_count = len(get_clinic_working_hours(clinic.id))
                    st.metric("Working Days Configured", working_hours_count)
                
                if st.button("❌ Delete Clinic", key=f"delete_{clinic.id}", type="primary"):
                    delete_clinic(clinic.id)
                    st.success("Clinic deleted successfully")
                    st.rerun()
    else:
        st.info("No clinics found. Add your first clinic above.")

elif menu == "Working Hours":
    st.title("⏰ Working Hours Configuration")
    
    clinics = get_all_clinics()
    if not clinics:
        st.warning("Please create a clinic first")
    else:
        clinic_options = {c.id: c.name for c in clinics}
        selected_clinic_id = st.selectbox("Select Clinic", options=list(clinic_options.keys()), format_func=lambda x: clinic_options[x])
        
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        current_hours = get_clinic_working_hours(selected_clinic_id)
        hours_map = {wh.day_of_week: wh for wh in current_hours}
        
        st.subheader("Edit Working Hours")
        updated_hours = []
        
        for day_num, day_name in enumerate(days):
            col1, col2, col3 = st.columns([2, 3, 3])
            
            with col1:
                enabled = st.checkbox(day_name, value=day_num in hours_map, key=f"enable_{selected_clinic_id}_{day_num}")
            
            with col2:
                start_val = hours_map[day_num].start_time if day_num in hours_map else time(9,0)
                start_time = st.time_input("Start", value=start_val, key=f"start_{selected_clinic_id}_{day_num}", disabled=not enabled)
            
            with col3:
                end_val = hours_map[day_num].end_time if day_num in hours_map else time(17,0)
                end_time = st.time_input("End", value=end_val, key=f"end_{selected_clinic_id}_{day_num}", disabled=not enabled)
            
            if enabled:
                updated_hours.append((day_num, start_time, end_time))
        
        if st.button("💾 Save Working Hours"):
            # Delete existing hours
            db.query(WorkingHours).filter(WorkingHours.tenant_id == selected_clinic_id).delete()
            
            # Add updated hours
            for day_num, start, end in updated_hours:
                db.add(WorkingHours(
                    tenant_id=selected_clinic_id,
                    day_of_week=day_num,
                    start_time=start,
                    end_time=end
                ))
            
            db.commit()
            st.success("✅ Working hours saved successfully!")

elif menu == "Appointments":
    st.title("📅 Appointments")
    
    appointments = get_all_appointments()
    if appointments:
        df = pd.DataFrame([{
            "ID": a.id,
            "Clinic": db.query(Clinic).get(a.tenant_id).name,
            "Patient Name": a.name,
            "Phone": a.phone,
            "Date": a.date,
            "Time": a.time,
            "Reason": a.reason
        } for a in appointments])
        
        st.dataframe(df, use_container_width=True)
        
        if st.button("🗑️ Delete All Appointments", type="primary"):
            db.query(Appointment).delete()
            db.commit()
            st.success("All appointments deleted")
            st.rerun()
    else:
        st.info("No appointments booked yet")

elif menu == "System":
    st.title("⚙️ System")
    
    st.subheader("Database Actions")
    
    if st.button("🔄 Reset Database & Load Sample Data"):
        from setup_sample_data import setup_sample_data
        setup_sample_data()
        st.success("✅ Database reset with sample data!")
        st.balloons()
    
    if st.button("❌ Clear All Data"):
        db.query(Appointment).delete()
        db.query(WorkingHours).delete()
        db.query(ClinicSettings).delete()
        db.query(Clinic).delete()
        db.commit()
        st.success("✅ All data cleared!")
        st.rerun()
    
    st.subheader("API Information")
    st.code("""
FastAPI Backend: http://localhost:8000
API Docs: http://localhost:8000/docs
Admin Dashboard: http://localhost:8501
    """)
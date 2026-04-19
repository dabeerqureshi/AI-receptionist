import streamlit as st
import pandas as pd
from datetime import datetime, date
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
import time

# Database setup - same as existing application
SQLALCHEMY_DATABASE_URL = "sqlite:///./receptionist.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Import existing Appointment model directly from application
import sys
sys.path.append('.')
from app.db.models import Appointment

# Page configuration
st.set_page_config(
    page_title="Appointments Dashboard",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded"
)

def get_db():
    db = SessionLocal()
    try:
        return db
    except:
        db.close()

def load_appointments(db):
    from app.db.models import Patient
    appointments = db.query(Appointment).order_by(desc(Appointment.date), desc(Appointment.start_time)).all()
    
    data = []
    for apt in appointments:
        patient = db.query(Patient).get(apt.patient_id)
        data.append({
            "ID": apt.id,
            "Patient Name": patient.name if patient else "",
            "Phone": patient.phone if patient else "",
            "Date": apt.date,
            "Start Time": apt.start_time,
            "End Time": apt.end_time,
            "Notes": apt.notes or "",
            "Created At": apt.created_at
        })
    
    df = pd.DataFrame(data)
    # Ensure columns exist even when empty
    expected_columns = ["ID", "Patient Name", "Phone", "Date", "Start Time", "End Time", "Notes", "Created At"]
    for col in expected_columns:
        if col not in df.columns:
            df[col] = pd.Series(dtype='object')
    
    return df

def main():
    st.title("📅 Appointments Realtime Dashboard")
    
    # Auto refresh setup
    refresh_interval = st.sidebar.slider("Refresh Interval (seconds)", 3, 30, 5)
    st.sidebar.info(f"Auto-refreshing every {refresh_interval} seconds")
    
    db = get_db()
    
    # Load data
    df = load_appointments(db)
    
    today = date.today()
    total_appointments = len(df)
    today_appointments = len(df[df["Date"] == today])
    upcoming_appointments = len(df[df["Date"] >= today])
    
    # Statistics cards
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Appointments", total_appointments)
    
    with col2:
        st.metric("Today's Appointments", today_appointments)
    
    with col3:
        st.metric("Upcoming Appointments", upcoming_appointments)
    
    st.divider()
    
    # Filters
    st.subheader("Filters")
    col1, col2 = st.columns(2)
    
    with col1:
        search_term = st.text_input("Search by Patient Name or Phone", "")
    
    with col2:
        date_filter = st.selectbox("View", ["All Appointments", "Today", "Upcoming", "Past"])
    
    # Apply filters
    filtered_df = df.copy()
    
    if search_term:
        filtered_df = filtered_df[
            filtered_df["Patient Name"].str.contains(search_term, case=False) |
            filtered_df["Phone"].str.contains(search_term, case=False)
        ]
    
    if date_filter == "Today":
        filtered_df = filtered_df[filtered_df["Date"] == today]
    elif date_filter == "Upcoming":
        filtered_df = filtered_df[filtered_df["Date"] >= today]
    elif date_filter == "Past":
        filtered_df = filtered_df[filtered_df["Date"] < today]
    
    st.divider()
    
    # Appointments table
    st.subheader("Appointments List")
    
    if len(filtered_df) == 0:
        st.info("No appointments found")
    else:
        # Style the dataframe
        def highlight_rows(row):
            if row["Date"] < today:
                return ['background-color: #fff3cd'] * len(row)
            elif row["Date"] == today:
                return ['background-color: #d1e7dd'] * len(row)
            else:
                return ['background-color: #cfe2ff'] * len(row)
        
        styled_df = filtered_df.style.apply(highlight_rows, axis=1)
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
    
    # Last updated time
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Auto refresh
    time.sleep(refresh_interval)
    st.rerun()

if __name__ == "__main__":
    main()
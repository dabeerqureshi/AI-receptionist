"""
AI Receptionist — Professional Admin Dashboard
Production-grade Streamlit dashboard with analytics, security, and UX polish.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import time, datetime, timedelta
from sqlalchemy.orm import Session
from database import SessionLocal, Clinic, ClinicSettings, WorkingHours, Appointment
import uuid
import os
import hashlib
import hmac
import secrets
import time as time_module
from dotenv import load_dotenv
import logging

# ─────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
)
logger = logging.getLogger("admin_dashboard")

# ─────────────────────────────────────────────
# Environment & Security
# ─────────────────────────────────────────────
load_dotenv()

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "").strip()
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH", "").strip()
SESSION_TIMEOUT_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES", "30"))
MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
LOCKOUT_MINUTES = int(os.getenv("LOCKOUT_MINUTES", "15"))


def hash_password(password: str) -> str:
    """SHA-256 password hashing (use bcrypt/argon2 in prod if possible)."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def check_credentials(username: str, password: str) -> bool:
    """Constant-time credential comparison to prevent timing attacks."""
    username_ok = hmac.compare_digest(username, ADMIN_USERNAME)
    password_ok = hmac.compare_digest(hash_password(password), ADMIN_PASSWORD_HASH)
    return username_ok and password_ok


def is_session_expired() -> bool:
    last_active = st.session_state.get("last_active")
    if last_active is None:
        return True
    return (datetime.now() - last_active).total_seconds() > SESSION_TIMEOUT_MINUTES * 60


def refresh_session():
    st.session_state["last_active"] = datetime.now()


# ─────────────────────────────────────────────
# Page Configuration
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="DentalFlow — AI Receptionist",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# Global CSS — Refined dark medical theme
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,300&family=DM+Serif+Display:ital@0;1&display=swap');

/* ── Shared design tokens ── */
:root {
    --accent:        #0284c7;
    --accent-dim:    #0369a1;
    --accent-glow:   rgba(2,132,199,0.12);
    --success:       #16a34a;
    --warning:       #b45309;
    --danger:        #dc2626;
    --serif:         'DM Serif Display', Georgia, serif;
    --sans:          'DM Sans', system-ui, sans-serif;
    --radius:        10px;
    --radius-lg:     16px;
}

/* ── Light mode (default) ── */
:root,
[data-theme="light"] {
    --bg-primary:    #f8fafc;
    --bg-card:       #ffffff;
    --bg-input:      #f1f5f9;
    --border:        #e2e8f0;
    --text-primary:  #0f172a;
    --text-secondary:#475569;
    --text-muted:    #94a3b8;
}

/* ── Dark mode ── */
[data-theme="dark"] {
    --bg-primary:    #0d1117;
    --bg-card:       #161b22;
    --bg-input:      #21262d;
    --border:        #30363d;
    --text-primary:  #e6edf3;
    --text-secondary:#8b949e;
    --text-muted:    #484f58;
}

@media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
        --bg-primary:    #0d1117;
        --bg-card:       #161b22;
        --bg-input:      #21262d;
        --border:        #30363d;
        --text-primary:  #e6edf3;
        --text-secondary:#8b949e;
        --text-muted:    #484f58;
    }
}

/* ── Global reset ── */
html, body, [class*="css"] {
    font-family: var(--sans) !important;
}

.main .block-container {
    padding: 2rem 2.5rem;
    max-width: 1400px;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background-color: var(--bg-card) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] * { color: var(--text-primary) !important; }
[data-testid="stSidebarNav"] { display: none; }

/* ── Page title ── */
.page-title {
    font-family: var(--serif);
    font-size: 2rem;
    font-weight: 400;
    letter-spacing: -0.02em;
    color: var(--text-primary);
    margin-bottom: 0.25rem;
}
.page-subtitle {
    font-size: 0.875rem;
    color: var(--text-secondary);
    margin-bottom: 2rem;
}

/* ── Metric cards ── */
.metric-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 1.4rem 1.6rem;
    position: relative;
    overflow: hidden;
    transition: border-color 0.2s;
}
.metric-card:hover { border-color: var(--accent-dim); }
.metric-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, var(--accent), transparent);
    border-radius: var(--radius-lg) var(--radius-lg) 0 0;
}
.metric-label {
    font-size: 0.75rem;
    font-weight: 500;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-secondary);
    margin-bottom: 0.6rem;
}
.metric-value {
    font-family: var(--serif);
    font-size: 2.4rem;
    color: var(--text-primary);
    line-height: 1;
    margin-bottom: 0.4rem;
}
.metric-delta {
    font-size: 0.8rem;
    color: var(--success);
}
.metric-icon {
    position: absolute;
    top: 1.2rem; right: 1.4rem;
    font-size: 1.6rem;
    opacity: 0.25;
}

/* ── Section header ── */
.section-header {
    font-size: 1rem;
    font-weight: 600;
    color: var(--text-primary);
    border-bottom: 1px solid var(--border);
    padding-bottom: 0.6rem;
    margin: 2rem 0 1rem;
    letter-spacing: -0.01em;
}

/* ── Status badge ── */
.badge {
    display: inline-block;
    padding: 0.2rem 0.65rem;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.04em;
}
.badge-success { background: rgba(63,185,80,0.15); color: var(--success); }
.badge-warning { background: rgba(210,153,34,0.15); color: var(--warning); }
.badge-danger  { background: rgba(248,81,73,0.15);  color: var(--danger);  }
.badge-info    { background: rgba(46,168,255,0.15); color: var(--accent);  }

/* ── Alert boxes ── */
.alert {
    border-radius: var(--radius);
    padding: 0.85rem 1.1rem;
    font-size: 0.875rem;
    border-left: 4px solid;
    margin: 0.8rem 0;
}
.alert-info    { background: var(--accent-glow);          border-color: var(--accent);  color: var(--accent);  }
.alert-success { background: rgba(63,185,80,0.1);         border-color: var(--success); color: var(--success); }
.alert-danger  { background: rgba(248,81,73,0.1);         border-color: var(--danger);  color: var(--danger);  }
.alert-warning { background: rgba(210,153,34,0.1);        border-color: var(--warning); color: var(--warning); }

/* ── Clinic card ── */
.clinic-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 1.4rem 1.6rem;
    margin-bottom: 1rem;
    transition: border-color 0.2s, box-shadow 0.2s;
}
.clinic-card:hover {
    border-color: var(--accent-dim);
    box-shadow: 0 0 0 1px var(--accent-dim), 0 4px 20px rgba(0,0,0,0.3);
}
.clinic-card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
}
.clinic-name {
    font-weight: 600;
    font-size: 1rem;
    color: var(--text-primary);
}
.clinic-id {
    font-size: 0.72rem;
    color: var(--text-muted);
    font-family: monospace;
}

/* ── Code / API key ── */
.api-key-box {
    background: var(--bg-primary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 0.6rem 0.9rem;
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 0.8rem;
    color: var(--accent);
    letter-spacing: 0.03em;
    word-break: break-all;
}

/* ── Streamlit widget overrides ── */
.stTextInput > div > div > input,
.stSelectbox > div > div,
.stNumberInput > div > div > input {
    background-color: var(--bg-input) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    color: var(--text-primary) !important;
}
.stTextInput > div > div > input:focus,
.stSelectbox > div > div:focus-within {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px var(--accent-glow) !important;
}

.stButton > button {
    background: var(--bg-input) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-primary) !important;
    border-radius: var(--radius) !important;
    font-weight: 500 !important;
    transition: all 0.15s !important;
}
.stButton > button:hover {
    background: var(--bg-card) !important;
    border-color: var(--accent) !important;
    color: var(--accent) !important;
}
button[kind="primary"] {
    background: var(--accent) !important;
    border-color: var(--accent) !important;
    color: #fff !important;
}
button[kind="primary"]:hover {
    background: #1e96e8 !important;
    color: #fff !important;
}

/* ── Dataframe ── */
[data-testid="stDataFrame"] {
    border-radius: var(--radius);
    border: 1px solid var(--border);
    overflow: hidden;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
}

/* ── Login card ── */
.login-container {
    max-width: 400px;
    margin: 6rem auto;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 2.5rem;
}
.login-logo {
    font-family: var(--serif);
    font-size: 1.8rem;
    text-align: center;
    margin-bottom: 0.25rem;
}
.login-subtitle {
    text-align: center;
    color: var(--text-secondary);
    font-size: 0.85rem;
    margin-bottom: 2rem;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg-primary); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }

/* ── Tab ── */
[data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid var(--border) !important;
    gap: 0 !important;
}
[data-baseweb="tab"] {
    background: transparent !important;
    color: var(--text-secondary) !important;
    font-size: 0.875rem !important;
    font-weight: 500 !important;
    padding: 0.6rem 1.2rem !important;
    border-radius: var(--radius) var(--radius) 0 0 !important;
}
[aria-selected="true"][data-baseweb="tab"] {
    color: var(--accent) !important;
    border-bottom: 2px solid var(--accent) !important;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Guard: env vars
# ─────────────────────────────────────────────
if not ADMIN_USERNAME or not ADMIN_PASSWORD_HASH:
    st.markdown("""
    <div class="alert alert-danger">
        ⚠️ <strong>Configuration error:</strong> ADMIN_USERNAME and ADMIN_PASSWORD_HASH must be set in <code>.env</code>.
    </div>
    """, unsafe_allow_html=True)
    st.stop()


# ─────────────────────────────────────────────
# Session-state initialisation
# ─────────────────────────────────────────────
defaults = {
    "authenticated": False,
    "last_active": None,
    "login_attempts": 0,
    "lockout_until": None,
}
for k, v in defaults.items():
    st.session_state.setdefault(k, v)


# ─────────────────────────────────────────────
# Database
# ─────────────────────────────────────────────
@st.cache_resource
def get_db_session():
    return SessionLocal()

db = get_db_session()


# ─────────────────────────────────────────────
# DB helpers
# ─────────────────────────────────────────────
def generate_api_key() -> str:
    return secrets.token_hex(16)   # 32-char cryptographically random hex

def get_all_clinics():
    return db.query(Clinic).all()

def get_clinic_settings(clinic_id):
    return db.query(ClinicSettings).filter(ClinicSettings.tenant_id == clinic_id).first()

def get_clinic_working_hours(clinic_id):
    return db.query(WorkingHours).filter(WorkingHours.tenant_id == clinic_id).all()

def get_all_appointments():
    return db.query(Appointment).all()

def delete_clinic(clinic_id):
    db.query(WorkingHours).filter(WorkingHours.tenant_id == clinic_id).delete()
    db.query(ClinicSettings).filter(ClinicSettings.tenant_id == clinic_id).delete()
    db.query(Appointment).filter(Appointment.tenant_id == clinic_id).delete()
    db.query(Clinic).filter(Clinic.id == clinic_id).delete()
    db.commit()
    logger.info("Clinic deleted: %s", clinic_id)

def get_appointments_df() -> pd.DataFrame:
    appts = get_all_appointments()
    if not appts:
        return pd.DataFrame()
    clinic_map = {c.id: c.name for c in get_all_clinics()}
    rows = []
    for a in appts:
        try:
            rows.append({
                "id": a.id,
                "clinic_id": a.tenant_id,
                "Clinic": clinic_map.get(a.tenant_id, "Unknown"),
                "Patient": a.name,
                "Phone": a.phone,
                "Date": pd.to_datetime(a.date),
                "Time": str(a.time),
                "Reason": a.reason,
            })
        except Exception as e:
            logger.warning("Skipping malformed appointment %s: %s", getattr(a, "id", "?"), e)
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────
# LOGIN WALL
# ─────────────────────────────────────────────
def show_login():
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.markdown('<div class="login-logo">🏥 DentalFlow</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-subtitle">AI Receptionist — Secure Admin Portal</div>', unsafe_allow_html=True)

    # Lockout check
    lockout_until = st.session_state.lockout_until
    if lockout_until and datetime.now() < lockout_until:
        remaining = int((lockout_until - datetime.now()).total_seconds() / 60) + 1
        st.markdown(f"""<div class="alert alert-danger">
            🔒 Too many failed attempts. Try again in {remaining} minute(s).</div>""",
            unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        return

    username = st.text_input("Username", placeholder="admin")
    password = st.text_input("Password", type="password", placeholder="••••••••")

    if st.button("Sign In", type="primary", width="stretch"):
        if check_credentials(username, password):
            st.session_state.authenticated = True
            st.session_state.last_active = datetime.now()
            st.session_state.login_attempts = 0
            st.session_state.lockout_until = None
            logger.info("Successful login for user: %s", username)
            st.rerun()
        else:
            st.session_state.login_attempts += 1
            attempts = st.session_state.login_attempts
            logger.warning("Failed login attempt %d for username: %s", attempts, username)
            if attempts >= MAX_LOGIN_ATTEMPTS:
                st.session_state.lockout_until = datetime.now() + timedelta(minutes=LOCKOUT_MINUTES)
                st.markdown(f"""<div class="alert alert-danger">
                    🔒 Account locked for {LOCKOUT_MINUTES} minutes after {MAX_LOGIN_ATTEMPTS} failed attempts.</div>""",
                    unsafe_allow_html=True)
            else:
                remaining = MAX_LOGIN_ATTEMPTS - attempts
                st.markdown(f"""<div class="alert alert-danger">
                    ❌ Invalid credentials. {remaining} attempt(s) remaining before lockout.</div>""",
                    unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

if not st.session_state.authenticated:
    show_login()
    st.stop()

# Session timeout check
if is_session_expired():
    st.session_state.authenticated = False
    st.session_state.last_active = None
    st.warning("⏱ Session expired. Please log in again.")
    st.rerun()

refresh_session()


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding: 0.5rem 0 1.5rem;">
        <div style="font-family: var(--serif); font-size: 1.4rem; color: var(--text-primary); margin-bottom: 0.15rem;">
            🏥 DentalFlow
        </div>
        <div style="font-size: 0.75rem; color: var(--text-muted);">AI Receptionist Console</div>
    </div>
    """, unsafe_allow_html=True)

    session_remaining = SESSION_TIMEOUT_MINUTES - int(
        (datetime.now() - st.session_state.last_active).total_seconds() / 60
    )
    st.markdown(f"""
    <div style="background:var(--bg-primary);border:1px solid var(--border);border-radius:var(--radius);
                padding:0.7rem 0.9rem;margin-bottom:1.2rem;">
        <div style="font-size:0.7rem;color:var(--text-muted);margin-bottom:0.2rem;">SIGNED IN AS</div>
        <div style="font-weight:600;font-size:0.875rem;">{ADMIN_USERNAME}</div>
        <div style="font-size:0.7rem;color:var(--text-muted);margin-top:0.3rem;">
            Session expires in ~{session_remaining}m
        </div>
    </div>
    """, unsafe_allow_html=True)

    menu = st.radio(
        "Navigation",
        ["📊 Dashboard", "📈 Analytics", "🏥 Clinics", "⏰ Working Hours", "📅 Appointments", "⚙️ System"],
        label_visibility="collapsed",
    )

    st.markdown("<div style='margin-top:auto;padding-top:2rem;'>", unsafe_allow_html=True)
    if st.button("🚪  Sign Out", width="stretch"):
        st.session_state.authenticated = False
        st.session_state.last_active = None
        logger.info("User signed out: %s", ADMIN_USERNAME)
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Plotly theme helper
# ─────────────────────────────────────────────
PLOT_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Sans, sans-serif", color="#6b7280", size=12),
    margin=dict(l=10, r=10, t=30, b=10),
)
# Axis defaults reused per-chart (avoids duplicate-key conflicts in update_layout)
_AXIS = dict(gridcolor="rgba(150,150,150,0.15)", linecolor="rgba(150,150,150,0.2)", zerolinecolor="rgba(150,150,150,0.15)")

def plot_layout(height=280, **extra):
    """Return a merged layout dict safe to pass to fig.update_layout()."""
    base = dict(**PLOT_LAYOUT, height=height,
                xaxis=dict(**_AXIS), yaxis=dict(**_AXIS))
    base.update(extra)
    return base

ACCENT = "#0284c7"
COLORS = ["#0284c7", "#16a34a", "#e8a838", "#ef4444", "#8b5cf6", "#f97316"]


def metric_card(label: str, value, icon: str, delta: str = ""):
    delta_html = f'<div class="metric-delta">↑ {delta}</div>' if delta else ""
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-icon">{icon}</div>
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# ── DASHBOARD ──────────────────────────────
# ─────────────────────────────────────────────
if menu == "📊 Dashboard":
    st.markdown('<div class="page-title">Overview Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Real-time summary of your clinic network</div>', unsafe_allow_html=True)

    total_clinics = db.query(Clinic).count()
    total_appointments = db.query(Appointment).count()
    total_wh = db.query(WorkingHours).count()
    df = get_appointments_df()

    today_count = 0
    week_count = 0
    if not df.empty:
        today = pd.Timestamp.now().normalize()
        week_start = today - pd.Timedelta(days=today.dayofweek)
        today_count = df[df["Date"] == today].shape[0]
        week_count = df[df["Date"] >= week_start].shape[0]

    cols = st.columns(4)
    with cols[0]: metric_card("Total Clinics", total_clinics, "🏥")
    with cols[1]: metric_card("All Appointments", total_appointments, "📅")
    with cols[2]: metric_card("Today's Bookings", today_count, "🗓️")
    with cols[3]: metric_card("This Week", week_count, "📆")

    st.markdown('<div class="section-header">Recent Appointments</div>', unsafe_allow_html=True)

    if not df.empty:
        display_df = df[["Clinic", "Patient", "Phone", "Date", "Time", "Reason"]].tail(15).copy()
        display_df["Date"] = display_df["Date"].dt.strftime("%d %b %Y")
        st.dataframe(display_df, width="stretch", hide_index=True)
    else:
        st.markdown('<div class="alert alert-info">ℹ️ No appointments recorded yet.</div>', unsafe_allow_html=True)

    # Quick activity timeline (last 30 days by day)
    if not df.empty and df.shape[0] > 2:
        st.markdown('<div class="section-header">Appointment Activity — Last 30 Days</div>', unsafe_allow_html=True)
        last_30 = df[df["Date"] >= (pd.Timestamp.now() - pd.Timedelta(days=30))]
        daily = last_30.groupby(last_30["Date"].dt.date).size().reset_index(name="Appointments")
        fig = go.Figure(go.Scatter(
            x=daily["Date"], y=daily["Appointments"],
            mode="lines+markers",
            line=dict(color=ACCENT, width=2),
            marker=dict(color=ACCENT, size=5),
            fill="tozeroy",
            fillcolor="rgba(2,132,199,0.07)",
        ))
        fig.update_layout(**plot_layout(220))
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


# ─────────────────────────────────────────────
# ── ANALYTICS ──────────────────────────────
# ─────────────────────────────────────────────
elif menu == "📈 Analytics":
    st.markdown('<div class="page-title">Analytics</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Appointment trends, clinic performance, and operational insights</div>', unsafe_allow_html=True)

    df = get_appointments_df()

    if df.empty:
        st.markdown('<div class="alert alert-warning">⚠️ Not enough data yet. Book some appointments to see analytics.</div>', unsafe_allow_html=True)
        st.stop()

    # ── Filters
    clinics_list = ["All"] + sorted(df["Clinic"].unique().tolist())
    with st.container():
        fcol1, fcol2, fcol3 = st.columns([2, 2, 3])
        with fcol1:
            clinic_filter = st.selectbox("Clinic", clinics_list)
        with fcol2:
            date_range = st.selectbox("Period", ["Last 7 days", "Last 30 days", "Last 90 days", "All time"])
        with fcol3:
            st.markdown("")  # spacer

    cutoffs = {
        "Last 7 days": pd.Timestamp.now() - pd.Timedelta(days=7),
        "Last 30 days": pd.Timestamp.now() - pd.Timedelta(days=30),
        "Last 90 days": pd.Timestamp.now() - pd.Timedelta(days=90),
        "All time": pd.Timestamp("2000-01-01"),
    }
    fdf = df[df["Date"] >= cutoffs[date_range]]
    if clinic_filter != "All":
        fdf = fdf[fdf["Clinic"] == clinic_filter]

    if fdf.empty:
        st.markdown('<div class="alert alert-info">ℹ️ No data for the selected filters.</div>', unsafe_allow_html=True)
        st.stop()

    # ── KPIs row
    total = len(fdf)
    unique_patients = fdf["Patient"].nunique()
    busiest_day_series = fdf.groupby(fdf["Date"].dt.day_name()).size()
    busiest_day = busiest_day_series.idxmax() if not busiest_day_series.empty else "—"
    top_clinic = fdf.groupby("Clinic").size().idxmax() if fdf["Clinic"].nunique() > 1 else (fdf["Clinic"].iloc[0] if not fdf.empty else "—")

    kcols = st.columns(4)
    with kcols[0]: metric_card("Appointments", total, "📅")
    with kcols[1]: metric_card("Unique Patients", unique_patients, "👤")
    with kcols[2]: metric_card("Busiest Day", busiest_day, "📆")
    with kcols[3]: metric_card("Top Clinic", top_clinic, "🏥")

    st.markdown("")

    # ── Row 1: Daily trend + By clinic
    r1c1, r1c2 = st.columns([3, 2])

    with r1c1:
        st.markdown('<div class="section-header">Daily Appointments</div>', unsafe_allow_html=True)
        daily = fdf.groupby(fdf["Date"].dt.date).size().reset_index(name="Appointments")
        fig1 = go.Figure(go.Bar(
            x=daily["Date"], y=daily["Appointments"],
            marker_color=ACCENT, marker_line_width=0,
        ))
        fig1.update_layout(**plot_layout(280, bargap=0.35))
        st.plotly_chart(fig1, width="stretch", config={"displayModeBar": False})

    with r1c2:
        st.markdown('<div class="section-header">By Clinic</div>', unsafe_allow_html=True)
        by_clinic = fdf.groupby("Clinic").size().reset_index(name="Count")
        fig2 = go.Figure(go.Pie(
            labels=by_clinic["Clinic"], values=by_clinic["Count"],
            hole=0.55,
            marker_colors=COLORS,
            textinfo="label+percent",
            textfont_size=11,
        ))
        fig2.update_layout(**plot_layout(280, showlegend=False))
        st.plotly_chart(fig2, width="stretch", config={"displayModeBar": False})

    # ── Row 2: By day of week + By hour
    r2c1, r2c2 = st.columns(2)

    with r2c1:
        st.markdown('<div class="section-header">By Day of Week</div>', unsafe_allow_html=True)
        day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        by_dow = fdf.groupby(fdf["Date"].dt.day_name()).size().reindex(day_order, fill_value=0).reset_index()
        by_dow.columns = ["Day", "Appointments"]
        fig3 = go.Figure(go.Bar(
            x=by_dow["Day"], y=by_dow["Appointments"],
            marker_color=[ACCENT if d not in ["Saturday", "Sunday"] else "rgba(150,150,150,0.35)" for d in by_dow["Day"]],
            marker_line_width=0,
        ))
        fig3.update_layout(**plot_layout(260, bargap=0.3))
        st.plotly_chart(fig3, width="stretch", config={"displayModeBar": False})

    with r2c2:
        st.markdown('<div class="section-header">Appointment Time Distribution</div>', unsafe_allow_html=True)
        try:
            fdf2 = fdf.copy()
            fdf2["Hour"] = fdf2["Time"].str[:2].astype(int)
            by_hour = fdf2.groupby("Hour").size().reset_index(name="Count")
            fig4 = go.Figure(go.Bar(
                x=by_hour["Hour"], y=by_hour["Count"],
                marker_color=COLORS[1], marker_line_width=0,
            ))
            layout4 = plot_layout(260, bargap=0.25)
            layout4["xaxis"].update(tickvals=list(range(8, 22)))
            fig4.update_layout(**layout4)
            st.plotly_chart(fig4, width="stretch", config={"displayModeBar": False})
        except Exception:
            st.markdown('<div class="alert alert-info">Time data unavailable for this chart.</div>', unsafe_allow_html=True)

    # ── Top reasons
    if "Reason" in fdf.columns:
        st.markdown('<div class="section-header">Top Appointment Reasons</div>', unsafe_allow_html=True)
        reasons = fdf["Reason"].dropna().value_counts().head(10).reset_index()
        reasons.columns = ["Reason", "Count"]
        fig5 = go.Figure(go.Bar(
            y=reasons["Reason"], x=reasons["Count"],
            orientation="h",
            marker_color=ACCENT, marker_line_width=0,
        ))
        layout5 = plot_layout(300)
        layout5["yaxis"].update(autorange="reversed")
        fig5.update_layout(**layout5)
        st.plotly_chart(fig5, width="stretch", config={"displayModeBar": False})

    # ── Export
    st.markdown('<div class="section-header">Export</div>', unsafe_allow_html=True)
    csv = fdf[["Clinic", "Patient", "Phone", "Date", "Time", "Reason"]].copy()
    csv["Date"] = csv["Date"].dt.strftime("%Y-%m-%d")
    st.download_button(
        "⬇️  Download CSV",
        csv.to_csv(index=False),
        file_name=f"appointments_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
    )


# ─────────────────────────────────────────────
# ── CLINICS ─────────────────────────────────
# ─────────────────────────────────────────────
elif menu == "🏥 Clinics":
    st.markdown('<div class="page-title">Clinics</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Create, configure and manage clinic tenants</div>', unsafe_allow_html=True)

    with st.expander("➕  Add New Clinic", expanded=False):
        with st.form("add_clinic_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                clinic_name = st.text_input("Clinic Name *", placeholder="e.g. Sunrise Family Clinic")
                timezone = st.selectbox("Timezone", [
                    "Asia/Karachi", "America/New_York", "America/Los_Angeles",
                    "Europe/London", "Europe/Paris", "Asia/Dubai",
                    "Asia/Singapore", "Asia/Kolkata", "UTC",
                ])
            with c2:
                appointment_duration = st.number_input(
                    "Appointment Duration (minutes)", min_value=10, max_value=180, value=30, step=5)
                max_daily = st.number_input(
                    "Max Daily Appointments", min_value=1, max_value=500, value=40)

            submitted = st.form_submit_button("✅  Create Clinic", type="primary")
            if submitted:
                if not clinic_name.strip():
                    st.markdown('<div class="alert alert-danger">❌ Clinic name is required.</div>', unsafe_allow_html=True)
                else:
                    clinic_id = f"clinic_{str(uuid.uuid4())[:8]}"
                    api_key = generate_api_key()

                    new_clinic = Clinic(id=clinic_id, name=clinic_name.strip(), api_key=api_key)
                    db.add(new_clinic)

                    new_settings = ClinicSettings(
                        tenant_id=clinic_id,
                        timezone=timezone,
                        appointment_duration=appointment_duration,
                    )
                    db.add(new_settings)

                    for day in range(5):
                        db.add(WorkingHours(
                            tenant_id=clinic_id, day_of_week=day,
                            start_time=time(9, 0), end_time=time(17, 0),
                        ))
                    db.commit()
                    logger.info("Clinic created: %s (id=%s)", clinic_name, clinic_id)

                    st.markdown(f"""
                    <div class="alert alert-success">
                        ✅ Clinic created! Save your API key — it won't be shown again.<br>
                        <div class="api-key-box" style="margin-top:0.6rem;">{api_key}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    st.balloons()

    st.markdown('<div class="section-header">Registered Clinics</div>', unsafe_allow_html=True)
    clinics = get_all_clinics()

    if not clinics:
        st.markdown('<div class="alert alert-info">ℹ️ No clinics yet. Create your first one above.</div>', unsafe_allow_html=True)
    else:
        df_appts = get_appointments_df()
        for clinic in clinics:
            settings = get_clinic_settings(clinic.id)
            wh_count = len(get_clinic_working_hours(clinic.id))
            appt_count = df_appts[df_appts["clinic_id"] == clinic.id].shape[0] if not df_appts.empty else 0

            with st.container():
                st.markdown(f"""
                <div class="clinic-card">
                    <div class="clinic-card-header">
                        <div>
                            <div class="clinic-name">🏥 {clinic.name}</div>
                            <div class="clinic-id">ID: {clinic.id}</div>
                        </div>
                        <span class="badge badge-success">Active</span>
                    </div>
                    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:1rem;font-size:0.8rem;">
                        <div>
                            <div style="color:var(--text-muted);margin-bottom:2px;">Timezone</div>
                            <div>{settings.timezone if settings else '—'}</div>
                        </div>
                        <div>
                            <div style="color:var(--text-muted);margin-bottom:2px;">Duration</div>
                            <div>{settings.appointment_duration if settings else '—'} min</div>
                        </div>
                        <div>
                            <div style="color:var(--text-muted);margin-bottom:2px;">Working Days</div>
                            <div>{wh_count}</div>
                        </div>
                        <div>
                            <div style="color:var(--text-muted);margin-bottom:2px;">Total Appointments</div>
                            <div>{appt_count}</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                with st.expander(f"Manage — {clinic.name}"):
                    tab1, tab2 = st.tabs(["🔑 API Key", "🗑️ Danger Zone"])

                    with tab1:
                        st.markdown("**Current API Key**")
                        st.markdown(f'<div class="api-key-box">{clinic.api_key}</div>', unsafe_allow_html=True)

                        if st.button("🔄 Rotate API Key", key=f"rotate_{clinic.id}"):
                            new_key = generate_api_key()
                            clinic.api_key = new_key
                            db.commit()
                            logger.info("API key rotated for clinic: %s", clinic.id)
                            st.markdown(f"""<div class="alert alert-success">
                                ✅ New key generated. Save it now!<br>
                                <div class="api-key-box" style="margin-top:0.5rem;">{new_key}</div>
                            </div>""", unsafe_allow_html=True)

                    with tab2:
                        st.markdown('<div class="alert alert-danger">⚠️ Deleting a clinic removes ALL associated data permanently.</div>', unsafe_allow_html=True)
                        confirm = st.text_input(
                            f'Type "{clinic.name}" to confirm deletion',
                            key=f"confirm_del_{clinic.id}",
                            placeholder=clinic.name,
                        )
                        if st.button("❌ Delete Clinic", key=f"delete_{clinic.id}"):
                            if confirm.strip() == clinic.name:
                                delete_clinic(clinic.id)
                                st.success("Clinic deleted.")
                                st.rerun()
                            else:
                                st.markdown('<div class="alert alert-danger">❌ Name does not match. Deletion cancelled.</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
# ── WORKING HOURS ──────────────────────────
# ─────────────────────────────────────────────
elif menu == "⏰ Working Hours":
    st.markdown('<div class="page-title">Working Hours</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Set availability for each clinic per day of week</div>', unsafe_allow_html=True)

    clinics = get_all_clinics()
    if not clinics:
        st.markdown('<div class="alert alert-warning">⚠️ Create a clinic first.</div>', unsafe_allow_html=True)
    else:
        clinic_options = {c.id: c.name for c in clinics}
        selected_clinic_id = st.selectbox(
            "Clinic", options=list(clinic_options.keys()),
            format_func=lambda x: clinic_options[x],
        )

        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        current_hours = get_clinic_working_hours(selected_clinic_id)
        hours_map = {wh.day_of_week: wh for wh in current_hours}

        st.markdown('<div class="section-header">Configure Hours</div>', unsafe_allow_html=True)
        updated_hours = []

        header_cols = st.columns([2, 3, 3, 1])
        header_cols[0].markdown('<small style="color:var(--text-muted)">DAY</small>', unsafe_allow_html=True)
        header_cols[1].markdown('<small style="color:var(--text-muted)">OPEN</small>', unsafe_allow_html=True)
        header_cols[2].markdown('<small style="color:var(--text-muted)">CLOSE</small>', unsafe_allow_html=True)
        header_cols[3].markdown('<small style="color:var(--text-muted)">ACTIVE</small>', unsafe_allow_html=True)

        for day_num, day_name in enumerate(days):
            col1, col2, col3, col4 = st.columns([2, 3, 3, 1])
            is_weekend = day_num >= 5

            with col1:
                st.markdown(
                    f'<div style="padding:0.55rem 0;color:{"var(--text-muted)" if is_weekend else "var(--text-primary)"};font-weight:{"400" if is_weekend else "500"}">{day_name}</div>',
                    unsafe_allow_html=True,
                )
            with col4:
                enabled = st.checkbox("", value=day_num in hours_map, key=f"en_{selected_clinic_id}_{day_num}", label_visibility="collapsed")

            with col2:
                sv = hours_map[day_num].start_time if day_num in hours_map else time(9, 0)
                start = st.time_input("Start", value=sv, key=f"s_{selected_clinic_id}_{day_num}",
                                      disabled=not enabled, label_visibility="collapsed")
            with col3:
                ev = hours_map[day_num].end_time if day_num in hours_map else time(17, 0)
                end = st.time_input("End", value=ev, key=f"e_{selected_clinic_id}_{day_num}",
                                    disabled=not enabled, label_visibility="collapsed")

            if enabled:
                if start >= end:
                    st.markdown(f'<div class="alert alert-danger">⚠️ {day_name}: close time must be after open time.</div>', unsafe_allow_html=True)
                else:
                    updated_hours.append((day_num, start, end))

        st.markdown("")
        if st.button("💾  Save Working Hours", type="primary"):
            db.query(WorkingHours).filter(WorkingHours.tenant_id == selected_clinic_id).delete()
            for day_num, start, end in updated_hours:
                db.add(WorkingHours(tenant_id=selected_clinic_id, day_of_week=day_num, start_time=start, end_time=end))
            db.commit()
            logger.info("Working hours updated for clinic: %s", selected_clinic_id)
            st.markdown('<div class="alert alert-success">✅ Working hours saved.</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
# ── APPOINTMENTS ───────────────────────────
# ─────────────────────────────────────────────
elif menu == "📅 Appointments":
    st.markdown('<div class="page-title">Appointments</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">View and manage all patient bookings</div>', unsafe_allow_html=True)

    df = get_appointments_df()

    if df.empty:
        st.markdown('<div class="alert alert-info">ℹ️ No appointments booked yet.</div>', unsafe_allow_html=True)
    else:
        # Filters
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            clinics_filter = ["All"] + sorted(df["Clinic"].unique().tolist())
            clinic_sel = st.selectbox("Filter by Clinic", clinics_filter)
        with fc2:
            search = st.text_input("Search Patient", placeholder="Name or phone…")
        with fc3:
            sort_by = st.selectbox("Sort by", ["Date ↓", "Date ↑", "Patient A–Z", "Clinic"])

        fdf = df.copy()
        if clinic_sel != "All":
            fdf = fdf[fdf["Clinic"] == clinic_sel]
        if search.strip():
            mask = (fdf["Patient"].str.contains(search, case=False, na=False) |
                    fdf["Phone"].str.contains(search, case=False, na=False))
            fdf = fdf[mask]

        sort_map = {
            "Date ↓": ("Date", False),
            "Date ↑": ("Date", True),
            "Patient A–Z": ("Patient", True),
            "Clinic": ("Clinic", True),
        }
        sort_col, sort_asc = sort_map[sort_by]
        fdf = fdf.sort_values(sort_col, ascending=sort_asc)

        st.markdown(f'<div style="font-size:0.8rem;color:var(--text-muted);margin:0.5rem 0;">'
                    f'Showing {len(fdf)} of {len(df)} records</div>', unsafe_allow_html=True)

        display_df = fdf[["Clinic", "Patient", "Phone", "Date", "Time", "Reason"]].copy()
        display_df["Date"] = display_df["Date"].dt.strftime("%d %b %Y")
        st.dataframe(display_df, width="stretch", hide_index=True)

        # Export + Delete
        ecol, dcol = st.columns([3, 1])
        with ecol:
            csv_bytes = display_df.to_csv(index=False)
            st.download_button("⬇️  Export Filtered CSV", csv_bytes,
                               file_name=f"appointments_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                               mime="text/csv")
        with dcol:
            if st.button("🗑️  Delete ALL", type="primary"):
                st.session_state["confirm_delete_all"] = True

        if st.session_state.get("confirm_delete_all"):
            st.markdown('<div class="alert alert-danger">⚠️ This will permanently delete every appointment record.</div>', unsafe_allow_html=True)
            cc1, cc2 = st.columns(2)
            with cc1:
                if st.button("✅ Yes, delete all"):
                    db.query(Appointment).delete()
                    db.commit()
                    st.session_state["confirm_delete_all"] = False
                    logger.warning("All appointments deleted by admin.")
                    st.rerun()
            with cc2:
                if st.button("Cancel"):
                    st.session_state["confirm_delete_all"] = False
                    st.rerun()


# ─────────────────────────────────────────────
# ── SYSTEM ──────────────────────────────────
# ─────────────────────────────────────────────
elif menu == "⚙️ System":
    st.markdown('<div class="page-title">System</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Health, configuration, and maintenance</div>', unsafe_allow_html=True)

    # Status
    st.markdown('<div class="section-header">Service Health</div>', unsafe_allow_html=True)
    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        db_ok = True
        try:
            db.query(Clinic).count()
        except Exception:
            db_ok = False
        badge = "badge-success" if db_ok else "badge-danger"
        label = "Connected" if db_ok else "Error"
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Database</div>
            <div><span class="badge {badge}">{label}</span></div>
        </div>""", unsafe_allow_html=True)

    with sc2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Session Timeout</div>
            <div style="font-size:1.4rem;font-weight:600;">{SESSION_TIMEOUT_MINUTES}m</div>
        </div>""", unsafe_allow_html=True)

    with sc3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Max Login Attempts</div>
            <div style="font-size:1.4rem;font-weight:600;">{MAX_LOGIN_ATTEMPTS} / {LOCKOUT_MINUTES}m lock</div>
        </div>""", unsafe_allow_html=True)

    # API Info
    st.markdown('<div class="section-header">API Endpoints</div>', unsafe_allow_html=True)
    st.code(
        "FastAPI Backend : http://localhost:8000\n"
        "API Docs (Swagger): http://localhost:8000/docs\n"
        "Admin Dashboard  : http://localhost:8501",
        language="text",
    )

    # Environment
    st.markdown('<div class="section-header">Environment Variables</div>', unsafe_allow_html=True)
    env_rows = {
        "ADMIN_USERNAME": "✅ Set" if ADMIN_USERNAME else "❌ Missing",
        "ADMIN_PASSWORD_HASH": "✅ Set" if ADMIN_PASSWORD_HASH else "❌ Missing",
        "SESSION_TIMEOUT_MINUTES": str(SESSION_TIMEOUT_MINUTES),
        "MAX_LOGIN_ATTEMPTS": str(MAX_LOGIN_ATTEMPTS),
        "LOCKOUT_MINUTES": str(LOCKOUT_MINUTES),
    }
    env_df = pd.DataFrame(list(env_rows.items()), columns=["Variable", "Status"])
    st.dataframe(env_df, width="stretch", hide_index=True)

    # Maintenance
    st.markdown('<div class="section-header">Maintenance</div>', unsafe_allow_html=True)
    st.markdown('<div class="alert alert-warning">⚠️ Destructive actions below. These cannot be undone.</div>', unsafe_allow_html=True)

    m1, m2 = st.columns(2)
    with m1:
        if st.button("🔄 Reset with Sample Data"):
            try:
                from setup_sample_data import setup_sample_data
                setup_sample_data()
                logger.info("Database reset with sample data.")
                st.markdown('<div class="alert alert-success">✅ Database reset with sample data.</div>', unsafe_allow_html=True)
            except ImportError:
                st.markdown('<div class="alert alert-danger">❌ setup_sample_data.py not found.</div>', unsafe_allow_html=True)

    with m2:
        if st.button("❌ Clear All Data"):
            st.session_state["confirm_clear_all"] = True

    if st.session_state.get("confirm_clear_all"):
        st.markdown('<div class="alert alert-danger">⚠️ This will wipe every clinic, appointment, and setting.</div>', unsafe_allow_html=True)
        yc, nc = st.columns(2)
        with yc:
            if st.button("✅ Confirm wipe"):
                db.query(Appointment).delete()
                db.query(WorkingHours).delete()
                db.query(ClinicSettings).delete()
                db.query(Clinic).delete()
                db.commit()
                st.session_state["confirm_clear_all"] = False
                logger.warning("All data wiped by admin.")
                st.rerun()
        with nc:
            if st.button("Cancel wipe"):
                st.session_state["confirm_clear_all"] = False
                st.rerun()
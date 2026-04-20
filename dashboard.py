import streamlit as st
import pandas as pd
from datetime import datetime, date
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
import time

# ── Database setup ──────────────────────────────────────────────────────────
SQLALCHEMY_DATABASE_URL = "sqlite:///./receptionist.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

import sys
sys.path.append(".")
from app.db.models import Appointment

# ── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ReceptAI · Appointments",
    page_icon="🗓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Premium CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Serif+Display&display=swap');

/* ── Root variables ── */
:root {
    --navy:       #0B1120;
    --navy2:      #111827;
    --navy3:      #1C2843;
    --navy4:      #243155;
    --gold:       #C9A84C;
    --gold2:      #E8C96B;
    --gold-dim:   rgba(201,168,76,0.10);
    --gold-glow:  rgba(201,168,76,0.06);
    --border:     #1E2E4A;
    --border-g:   rgba(201,168,76,0.22);
    --text-p:     #F0EDE6;
    --text-s:     #8C9BB8;
    --text-m:     #566180;
    --green:      #4ECFA0;
    --blue:       #5B9CF6;
    --red:        #E05C6A;
}

/* ── Global reset & font ── */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif !important;
    background-color: var(--navy) !important;
    color: var(--text-p) !important;
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }

/* ── App background ── */
.stApp { background-color: var(--navy) !important; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background-color: var(--navy2) !important;
    border-right: 1px solid var(--border) !important;
}
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] label {
    color: var(--text-s) !important;
    font-size: 0.83rem !important;
}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    color: var(--gold) !important;
    font-family: 'DM Serif Display', serif !important;
    font-size: 1.1rem !important;
}

/* ── Sidebar slider ── */
.stSlider > div > div > div {
    background: var(--gold) !important;
}
.stSlider > div > div > div > div {
    background: var(--gold) !important;
    border: 2px solid var(--gold2) !important;
}

/* ── Sidebar info box ── */
.stAlert {
    background-color: var(--gold-dim) !important;
    border: 1px solid var(--border-g) !important;
    border-radius: 10px !important;
    color: var(--gold) !important;
}
.stAlert p { color: var(--gold) !important; font-size: 0.82rem !important; }

/* ── Page title ── */
h1 {
    font-family: 'DM Serif Display', serif !important;
    color: var(--text-p) !important;
    font-size: 2rem !important;
    font-weight: 400 !important;
    letter-spacing: -0.01em !important;
    border-bottom: 1px solid var(--border) !important;
    padding-bottom: 0.6rem !important;
    margin-bottom: 0.2rem !important;
}
h2, h3 {
    color: var(--text-p) !important;
    font-weight: 500 !important;
    font-size: 0.95rem !important;
    letter-spacing: 0.05em !important;
    text-transform: uppercase !important;
}

/* ── Metric cards ── */
div[data-testid="stMetric"] {
    background-color: var(--navy2) !important;
    border: 1px solid var(--border) !important;
    border-top: 2px solid var(--gold) !important;
    border-radius: 14px !important;
    padding: 1.3rem 1.4rem !important;
    transition: border-color 0.2s, transform 0.2s !important;
}
div[data-testid="stMetric"]:hover {
    border-color: var(--border-g) !important;
    transform: translateY(-2px) !important;
}
div[data-testid="stMetricLabel"] p {
    color: var(--text-m) !important;
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
}
div[data-testid="stMetricValue"] {
    color: var(--text-p) !important;
    font-size: 2.1rem !important;
    font-weight: 300 !important;
    letter-spacing: -0.02em !important;
}
div[data-testid="stMetricDelta"] {
    font-size: 0.75rem !important;
}

/* ── Divider ── */
hr {
    border: none !important;
    border-top: 1px solid var(--border) !important;
    margin: 0.4rem 0 !important;
}

/* ── Search input ── */
.stTextInput > div > div > input {
    background-color: var(--navy2) !important;
    border: 1px solid var(--border) !important;
    border-radius: 9px !important;
    color: var(--text-p) !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.85rem !important;
    padding: 0.55rem 0.9rem !important;
    transition: border-color 0.15s !important;
}
.stTextInput > div > div > input:focus {
    border-color: var(--border-g) !important;
    box-shadow: 0 0 0 3px rgba(201,168,76,0.1) !important;
}
.stTextInput > div > div > input::placeholder { color: var(--text-m) !important; }
.stTextInput label { color: var(--text-s) !important; font-size: 0.78rem !important; }

/* ── Selectbox ── */
.stSelectbox > div > div {
    background-color: var(--navy2) !important;
    border: 1px solid var(--border) !important;
    border-radius: 9px !important;
    color: var(--text-p) !important;
    font-size: 0.85rem !important;
}
.stSelectbox > div > div:focus-within {
    border-color: var(--border-g) !important;
}
.stSelectbox label { color: var(--text-s) !important; font-size: 0.78rem !important; }

/* ── Dataframe ── */
.stDataFrame {
    border: 1px solid var(--border) !important;
    border-radius: 14px !important;
    overflow: hidden !important;
}
.stDataFrame iframe {
    border-radius: 14px !important;
}

/* Dataframe inner table (rendered via Streamlit's AgGrid-style component) */
[data-testid="stDataFrameResizable"] {
    border-radius: 12px !important;
    overflow: hidden !important;
    border: 1px solid var(--border) !important;
}

/* ── Buttons ── */
.stButton > button {
    background: linear-gradient(135deg, var(--gold), #9A7530) !important;
    color: #0B1120 !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.82rem !important;
    letter-spacing: 0.03em !important;
    padding: 0.5rem 1.2rem !important;
    transition: all 0.15s !important;
    box-shadow: 0 4px 14px rgba(201,168,76,0.2) !important;
}
.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(201,168,76,0.35) !important;
}

/* ── Caption / small text ── */
.stCaption, small, .caption {
    color: var(--text-m) !important;
    font-size: 0.75rem !important;
}

/* ── Status tag HTML ── */
.badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 500;
    font-family: 'DM Sans', sans-serif;
}
.badge-today    { background: rgba(91,156,246,0.12); color: #5B9CF6; border: 1px solid rgba(91,156,246,0.25); }
.badge-upcoming { background: rgba(78,207,160,0.09); color: #4ECFA0; border: 1px solid rgba(78,207,160,0.22); }
.badge-past     { background: rgba(86,97,128,0.14);  color: #566180; border: 1px solid rgba(86,97,128,0.22); }

/* ── Live refresh indicator ── */
.live-pill {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    background: rgba(78,207,160,0.09);
    border: 1px solid rgba(78,207,160,0.22);
    border-radius: 20px;
    padding: 4px 12px;
    font-size: 0.72rem;
    font-weight: 500;
    color: #4ECFA0;
    font-family: 'DM Sans', sans-serif;
}
.live-dot {
    width: 6px; height: 6px;
    border-radius: 50%;
    background: #4ECFA0;
    animation: livepulse 2s ease infinite;
    display: inline-block;
}
@keyframes livepulse {
    0%,100% { opacity:1; transform:scale(1); }
    50%      { opacity:.5; transform:scale(.85); }
}

/* ── Page header strip ── */
.page-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1.2rem;
}
.brand {
    display: flex;
    align-items: center;
    gap: 10px;
}
.brand-name {
    font-family: 'DM Serif Display', serif;
    font-size: 1.05rem;
    color: var(--text-p);
    letter-spacing: 0.01em;
}
.brand-name span { color: var(--gold); }

/* ── Section label ── */
.section-label {
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--text-m);
    margin-bottom: 0.5rem;
    font-family: 'DM Sans', sans-serif;
}

/* ── Row highlight helper ── */
.row-today    { background: rgba(91,156,246,0.07) !important; }
.row-upcoming { background: rgba(78,207,160,0.04) !important; }
.row-past     { opacity: 0.6; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ─────────────────────────────────────────────────────────────────
def get_db():
    return SessionLocal()


def load_appointments(db) -> pd.DataFrame:
    from app.db.models import Patient

    appointments = (
        db.query(Appointment)
        .order_by(desc(Appointment.date), desc(Appointment.start_time))
        .all()
    )

    rows = []
    for apt in appointments:
        patient = db.get(Patient, apt.patient_id)
        rows.append({
            "ID":           apt.id,
            "Patient":      patient.name if patient else "—",
            "Phone":        patient.phone if patient else "—",
            "Date":         apt.date,
            "Start":        apt.start_time,
            "End":          apt.end_time,
            "Notes":        apt.notes or "",
            "Created":      apt.created_at,
        })

    df = pd.DataFrame(rows)
    expected = ["ID", "Patient", "Phone", "Date", "Start", "End", "Notes", "Created"]
    for col in expected:
        if col not in df.columns:
            df[col] = pd.Series(dtype="object")
    return df


def status_badge(appt_date: date) -> str:
    today = date.today()
    if appt_date == today:
        return '<span class="badge badge-today">● Today</span>'
    if appt_date > today:
        return '<span class="badge badge-upcoming">● Upcoming</span>'
    return '<span class="badge badge-past">● Past</span>'


def duration(start, end) -> str:
    try:
        fmt = "%H:%M:%S" if len(str(start)) > 5 else "%H:%M"
        s = datetime.strptime(str(start), fmt)
        e = datetime.strptime(str(end), fmt)
        mins = int((e - s).total_seconds() / 60)
        return f"{mins} min" if mins > 0 else "—"
    except Exception:
        return "—"


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:0.4rem 0 1.2rem">
        <div style="font-family:'DM Serif Display',serif;font-size:1.25rem;color:#F0EDE6;">
            Recept<span style="color:#C9A84C;">AI</span>
        </div>
        <div style="font-size:0.72rem;color:#566180;margin-top:2px;letter-spacing:0.04em;">
            Appointments Platform
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    st.markdown('<div class="section-label">Auto-Refresh</div>', unsafe_allow_html=True)
    refresh_interval = st.slider("Interval (seconds)", 3, 30, 5, label_visibility="collapsed")
    st.info(f"🔄 Refreshing every **{refresh_interval}s**")

    st.divider()

    st.markdown('<div class="section-label">Navigation</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="display:flex;flex-direction:column;gap:4px;margin-top:6px">
        <div style="padding:8px 12px;border-radius:8px;background:rgba(201,168,76,0.10);
                    border:1px solid rgba(201,168,76,0.22);color:#C9A84C;font-size:0.82rem;
                    font-weight:500;display:flex;align-items:center;gap:8px">
            🗓 Appointments
        </div>
        <div style="padding:8px 12px;border-radius:8px;color:#566180;font-size:0.82rem;
                    cursor:pointer;display:flex;align-items:center;gap:8px">
            👤 Patients
        </div>
        <div style="padding:8px 12px;border-radius:8px;color:#566180;font-size:0.82rem;
                    cursor:pointer;display:flex;align-items:center;gap:8px">
            📊 Analytics
        </div>
        <div style="padding:8px 12px;border-radius:8px;color:#566180;font-size:0.82rem;
                    cursor:pointer;display:flex;align-items:center;gap:8px">
            ⚙️ Settings
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    st.markdown("""
    <div style="background:rgba(201,168,76,0.06);border:1px solid rgba(201,168,76,0.18);
                border-radius:10px;padding:14px;margin-top:6px">
        <div style="color:#C9A84C;font-size:0.8rem;font-weight:600;margin-bottom:4px">
            Upgrade to Pro
        </div>
        <div style="color:#566180;font-size:0.75rem;line-height:1.5">
            AI scheduling, SMS reminders &amp; advanced analytics.
        </div>
    </div>
    """, unsafe_allow_html=True)


# ── Main ─────────────────────────────────────────────────────────────────────
# Header row
col_title, col_live = st.columns([5, 1])
with col_title:
    st.markdown("# 🗓 Appointments")
    st.markdown(
        '<div style="color:#566180;font-size:0.8rem;margin-top:-6px">'
        'Real-time view · auto-refreshing</div>',
        unsafe_allow_html=True,
    )
with col_live:
    st.markdown(
        f'<div style="padding-top:1.4rem">'
        f'<span class="live-pill"><span class="live-dot"></span>Live</span>'
        f"</div>",
        unsafe_allow_html=True,
    )

st.divider()

# ── Load data ────────────────────────────────────────────────────────────────
db = get_db()
df = load_appointments(db)

today = date.today()
total        = len(df)
today_count  = int((df["Date"] == today).sum()) if not df.empty else 0
upcoming     = int((df["Date"] > today).sum())  if not df.empty else 0
past         = int((df["Date"] < today).sum())  if not df.empty else 0

# ── Metric cards ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">Overview</div>', unsafe_allow_html=True)
m1, m2, m3, m4 = st.columns(4)
m1.metric("📋 Total",    total,        delta="+12% this month")
m2.metric("📅 Today",    today_count,  delta="+3 since yesterday")
m3.metric("⏰ Upcoming", upcoming,     delta="On track")
m4.metric("🕐 Past",     past,         delta=None)

st.divider()

# ── Filters ───────────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">Filters</div>', unsafe_allow_html=True)
fc1, fc2 = st.columns([3, 2])
with fc1:
    search = st.text_input(
        "Search appointments",
        placeholder="🔍  Search patient name or phone…",
        label_visibility="collapsed",
    )
with fc2:
    view_filter = st.selectbox(
        "Appointment view",
        ["All Appointments", "Today", "Upcoming", "Past"],
        label_visibility="collapsed",
    )

st.divider()

# ── Apply filters ─────────────────────────────────────────────────────────────
filtered = df.copy()

if search:
    q = search.lower()
    filtered = filtered[
        filtered["Patient"].str.lower().str.contains(q, na=False)
        | filtered["Phone"].str.lower().str.contains(q, na=False)
    ]

if view_filter == "Today":
    filtered = filtered[filtered["Date"] == today]
elif view_filter == "Upcoming":
    filtered = filtered[filtered["Date"] > today]
elif view_filter == "Past":
    filtered = filtered[filtered["Date"] < today]

# ── Table ─────────────────────────────────────────────────────────────────────
header_col, count_col = st.columns([5, 1])
with header_col:
    st.markdown('<div class="section-label">Appointment Records</div>', unsafe_allow_html=True)
with count_col:
    st.markdown(
        f'<div style="text-align:right;padding-top:2px">'
        f'<span style="background:#1C2843;border:1px solid #1E2E4A;border-radius:20px;'
        f'padding:3px 10px;font-size:0.72rem;color:#566180">'
        f'{len(filtered)} record{"s" if len(filtered) != 1 else ""}</span></div>',
        unsafe_allow_html=True,
    )

if filtered.empty:
    st.markdown(
        '<div style="text-align:center;padding:3rem 1rem;color:#566180;font-size:0.9rem">'
        "📋 No appointments match your criteria</div>",
        unsafe_allow_html=True,
    )
else:
    # Build display dataframe
    display = filtered.copy()
    display["Duration"] = display.apply(lambda r: duration(r["Start"], r["End"]), axis=1)
    display["Notes"] = display["Notes"].replace("", "—")

    # Row styling
    def row_style(row):
        d = row["Date"]
        if d == today:
            bg = "background-color: rgba(91,156,246,0.08); color: #F0EDE6"
        elif d > today:
            bg = "background-color: rgba(78,207,160,0.04); color: #F0EDE6"
        else:
            bg = "background-color: transparent; color: #566180"
        return [bg] * len(row)

    show_cols = ["Patient", "Phone", "Date", "Start", "End", "Duration", "Notes"]
    styled = (
        display[show_cols]
        .style.apply(row_style, axis=1)
        .set_properties(**{
            "font-family": "'DM Sans', sans-serif",
            "font-size":   "13px",
        })
        .set_table_styles([
            {
                "selector": "thead th",
                "props": [
                    ("background-color", "#0B1120"),
                    ("color", "#566180"),
                    ("font-size", "10px"),
                    ("font-weight", "600"),
                    ("letter-spacing", "0.08em"),
                    ("text-transform", "uppercase"),
                    ("padding", "11px 16px"),
                    ("border-bottom", "1px solid #1E2E4A"),
                ],
            },
            {
                "selector": "tbody td",
                "props": [
                    ("padding", "12px 16px"),
                    ("border-bottom", "1px solid rgba(30,46,74,0.6)"),
                ],
            },
            {
                "selector": "table",
                "props": [
                    ("border-collapse", "collapse"),
                    ("width", "100%"),
                    ("background-color", "#111827"),
                ],
            },
        ])
    )

    st.dataframe(
        display[show_cols],
        width="stretch",
        hide_index=True,
        height=min(48 * len(display) + 48, 520),
        column_config={
            "Date":     st.column_config.DateColumn("Date", format="DD MMM YYYY"),
            "Duration": st.column_config.TextColumn("Duration"),
            "Notes":    st.column_config.TextColumn("Notes", width="large"),
        },
    )

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(
    f'<div style="text-align:right;color:#566180;font-size:0.72rem;'
    f'margin-top:0.6rem;font-style:italic">'
    f'Last synced · {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
    f"</div>",
    unsafe_allow_html=True,
)

# ── Auto-refresh ──────────────────────────────────────────────────────────────
time.sleep(refresh_interval)
db.close()
st.rerun()

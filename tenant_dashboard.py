"""
Clinic AI Receptionist Dashboard
Production-grade, secure, multi-tenant Streamlit application.
Dark/light mode adaptive — all colours via CSS custom properties.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date, time, timedelta
import os
import secrets
import logging
from dotenv import load_dotenv
from api_client import (
    APIError,
    tenant_create_appointment,
    tenant_delete_appointment,
    tenant_get_appointment,
    tenant_get_appointments,
    tenant_get_clinic,
    tenant_get_settings,
    tenant_get_working_hours,
    tenant_update_appointment,
    tenant_update_settings,
    tenant_update_working_hours,
    tenant_verify_credentials,
)

# ──────────────────────────────────────────────
# Bootstrap
# ──────────────────────────────────────────────
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("clinic_dashboard")

# ──────────────────────────────────────────────
# Page Config  (must be first Streamlit call)
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="Clinic AI Receptionist",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": None,
        "Report a bug": None,
        "About": "Clinic AI Receptionist Dashboard — Secure Multi-Tenant",
    },
)

# ──────────────────────────────────────────────
# CSS — all colours expressed as CSS custom
# properties so both light and dark mode work
# automatically, driven by prefers-color-scheme.
# Streamlit's own dark-theme toggle also flips
# this media query, so both paths are handled.
# ──────────────────────────────────────────────
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=DM+Mono:wght@400;500&display=swap');

/* ═══════════════════════════════════════════
   DESIGN TOKENS — light mode
   ═══════════════════════════════════════════ */
:root {
    --brand-900:  #0a1628;
    --brand-700:  #1e3a5f;
    --brand-500:  #2563eb;
    --brand-300:  #93c5fd;
    --brand-100:  #dbeafe;
    --brand-50:   #eff6ff;

    --bg-app:     #f0f4f8;
    --bg-card:    #ffffff;
    --bg-raised:  #f8fafc;

    --border:       #e2e8f0;
    --border-focus: #2563eb;

    --text-primary:   #0a1628;
    --text-secondary: #334155;
    --text-muted:     #64748b;
    --text-faint:     #94a3b8;

    /* Sidebar always stays dark regardless of mode */
    --sb-bg:     #0a1628;
    --sb-border: #1e3a5f;
    --sb-text:   #c8d8ea;
    --sb-muted:  #475569;

    /* Semantic colour surfaces */
    --warn-bg:     #fef9c3;
    --warn-text:   #854d0e;
    --warn-border: #fde68a;
    --info-bg:     #dbeafe;
    --info-text:   #1e40af;
    --info-border: #93c5fd;
    --ok-bg:       #dcfce7;
    --ok-text:     #166534;
    --ok-border:   #86efac;

    /* Plotly surfaces (exposed to Python via data attr) */
    --chart-bg:   #ffffff;
    --chart-grid: #f1f5f9;
    --chart-text: #334155;
    --chart-line: #2563eb;
    --chart-bar:  #1e3a5f;

    --shadow-sm: 0 1px 3px rgba(0,0,0,0.06);
    --shadow-md: 0 4px 14px rgba(10,22,40,0.12);
    --shadow-lg: 0 8px 40px rgba(0,0,0,0.08);
}

/* ═══════════════════════════════════════════
   DESIGN TOKENS — dark mode
   ═══════════════════════════════════════════ */
@media (prefers-color-scheme: dark) {
    :root {
        --brand-900:  #172033;
        --brand-700:  #1e3a5f;
        --brand-500:  #60a5fa;
        --brand-300:  #2563eb;
        --brand-100:  #1e3a5f;
        --brand-50:   #172033;

        --bg-app:     #0f172a;
        --bg-card:    #1e293b;
        --bg-raised:  #162032;

        --border:       #334155;
        --border-focus: #60a5fa;

        --text-primary:   #f1f5f9;
        --text-secondary: #cbd5e1;
        --text-muted:     #94a3b8;
        --text-faint:     #64748b;

        --warn-bg:     #422006;
        --warn-text:   #fde68a;
        --warn-border: #78350f;
        --info-bg:     #172033;
        --info-text:   #93c5fd;
        --info-border: #1e3a5f;
        --ok-bg:       #14532d;
        --ok-text:     #86efac;
        --ok-border:   #166534;

        --chart-bg:   #1e293b;
        --chart-grid: #334155;
        --chart-text: #94a3b8;
        --chart-line: #60a5fa;
        --chart-bar:  #3b82f6;

        --shadow-sm: 0 1px 3px rgba(0,0,0,0.35);
        --shadow-md: 0 4px 14px rgba(0,0,0,0.45);
        --shadow-lg: 0 8px 40px rgba(0,0,0,0.55);
    }
}

/* ═══════════════════════════════════════════
   GLOBALS
   ═══════════════════════════════════════════ */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif !important;
}
.stApp {
    background: var(--bg-app) !important;
}
p, li, span, div {
    color: var(--text-primary);
}

/* ═══════════════════════════════════════════
   SIDEBAR — always dark navy
   ═══════════════════════════════════════════ */
section[data-testid="stSidebar"] {
    background: var(--sb-bg) !important;
    border-right: 1px solid var(--sb-border) !important;
}
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] div {
    color: var(--sb-text) !important;
}
section[data-testid="stSidebar"] .stRadio label {
    padding: 0.45rem 0.75rem;
    border-radius: 8px;
    cursor: pointer;
    transition: background 0.18s;
}
section[data-testid="stSidebar"] .stRadio label:hover {
    background: rgba(255,255,255,0.07) !important;
}
section[data-testid="stSidebar"] hr {
    border-color: var(--sb-border) !important;
}
section[data-testid="stSidebar"] .stButton > button {
    background: rgba(255,255,255,0.07) !important;
    border: 1px solid var(--sb-border) !important;
    color: var(--sb-text) !important;
    border-radius: 8px !important;
    font-size: 0.85rem !important;
    transition: background 0.18s !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,0.13) !important;
}

/* ═══════════════════════════════════════════
   METRIC CARDS
   ═══════════════════════════════════════════ */
[data-testid="metric-container"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 14px !important;
    padding: 1.25rem 1.5rem !important;
    box-shadow: var(--shadow-sm) !important;
}
[data-testid="metric-container"] label {
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.07em !important;
    text-transform: uppercase !important;
    color: var(--text-muted) !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-size: 2rem !important;
    font-weight: 700 !important;
    color: var(--text-primary) !important;
    line-height: 1.15 !important;
}

/* ═══════════════════════════════════════════
   DATAFRAME
   ═══════════════════════════════════════════ */
[data-testid="stDataFrame"] {
    border-radius: 12px !important;
    overflow: hidden !important;
    border: 1px solid var(--border) !important;
}

/* ═══════════════════════════════════════════
   BUTTONS
   ═══════════════════════════════════════════ */
.stButton > button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 0.875rem !important;
    font-family: 'DM Sans', sans-serif !important;
    border: 1px solid var(--border) !important;
    background: var(--bg-card) !important;
    color: var(--text-primary) !important;
    transition: all 0.18s ease !important;
}
.stButton > button:hover {
    border-color: var(--brand-500) !important;
    color: var(--brand-500) !important;
}
.stButton > button[kind="primary"] {
    background: var(--brand-700) !important;
    border-color: var(--brand-700) !important;
    color: #ffffff !important;
}
.stButton > button[kind="primary"]:hover {
    background: var(--brand-500) !important;
    border-color: var(--brand-500) !important;
    color: #ffffff !important;
    transform: translateY(-1px) !important;
    box-shadow: var(--shadow-md) !important;
}

/* ═══════════════════════════════════════════
   FORM INPUTS
   ═══════════════════════════════════════════ */
.stTextInput input,
.stNumberInput input,
.stTextArea textarea {
    border-radius: 8px !important;
    border: 1.5px solid var(--border) !important;
    background: var(--bg-card) !important;
    color: var(--text-primary) !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.9rem !important;
    transition: border-color 0.18s, box-shadow 0.18s !important;
}
.stTextInput input:focus,
.stNumberInput input:focus,
.stTextArea textarea:focus {
    border-color: var(--border-focus) !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,0.14) !important;
    outline: none !important;
}
.stTextInput input:disabled,
.stNumberInput input:disabled,
.stTextArea textarea:disabled {
    opacity: 0.55 !important;
    cursor: not-allowed !important;
}

/* Form labels */
.stTextInput label,
.stNumberInput label,
.stTextArea label,
.stSelectbox label,
.stDateInput label,
.stTimeInput label,
.stCheckbox label,
.stRadio label {
    color: var(--text-secondary) !important;
    font-weight: 500 !important;
    font-size: 0.875rem !important;
}
/* Caption / hint text */
.stCaption, small, [data-testid="stCaptionContainer"] {
    color: var(--text-muted) !important;
}

/* ═══════════════════════════════════════════
   EXPANDERS
   ═══════════════════════════════════════════ */
[data-testid="stExpander"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
}
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary p {
    color: var(--text-primary) !important;
    font-weight: 600 !important;
}

/* ═══════════════════════════════════════════
   HEADINGS
   ═══════════════════════════════════════════ */
h1 {
    font-size: 1.75rem !important;
    font-weight: 700 !important;
    color: var(--text-primary) !important;
    letter-spacing: -0.02em !important;
}
h2 {
    font-size: 1.2rem !important;
    font-weight: 600 !important;
    color: var(--text-secondary) !important;
}
h3 {
    font-size: 1rem !important;
    font-weight: 600 !important;
    color: var(--text-secondary) !important;
}

/* ═══════════════════════════════════════════
   DIVIDERS
   ═══════════════════════════════════════════ */
hr { border-color: var(--border) !important; }

/* ═══════════════════════════════════════════
   PAGE HEADER STRIP
   Always a dark gradient so white text is safe
   in both light and dark modes.
   ═══════════════════════════════════════════ */
.ph {
    background: linear-gradient(135deg, #0a1628 0%, #1e3a5f 100%);
    border-radius: 16px;
    padding: 1.5rem 2rem;
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    gap: 1rem;
}
.ph-icon  { font-size: 2rem; line-height: 1; }
.ph-title { font-size: 1.4rem; font-weight: 700; color: #f1f5f9 !important; margin: 0; letter-spacing: -0.02em; }
.ph-sub   { font-size: 0.83rem; color: #94a3b8 !important; margin: 0.15rem 0 0; }

/* ═══════════════════════════════════════════
   NOTICE BOXES — use CSS vars, invert in dark
   ═══════════════════════════════════════════ */
.notice {
    border-radius: 10px;
    padding: .75rem 1rem;
    font-size: .84rem;
    margin: .5rem 0 1rem;
    border: 1px solid;
    line-height: 1.55;
}
.notice-warning { background: var(--warn-bg); color: var(--warn-text); border-color: var(--warn-border); }
.notice-info    { background: var(--info-bg); color: var(--info-text); border-color: var(--info-border); }
.notice-ok      { background: var(--ok-bg);   color: var(--ok-text);   border-color: var(--ok-border);   }

/* ═══════════════════════════════════════════
   SESSION INFO BOX (Settings page)
   ═══════════════════════════════════════════ */
.session-box {
    padding: .65rem 1rem;
    background: var(--bg-raised);
    border: 1px solid var(--border);
    border-radius: 8px;
    font-size: .82rem;
    color: var(--text-muted);
}

/* ═══════════════════════════════════════════
   LOGIN PAGE
   ═══════════════════════════════════════════ */
.login-hero {
    text-align: center;
    padding: 2rem 0 1.25rem;
}
.login-hero h1 {
    color: var(--text-primary) !important;
    font-size: 1.6rem !important;
    margin: .5rem 0 .25rem;
}
.login-hero p {
    color: var(--text-muted) !important;
    font-size: .9rem;
}
.login-footer {
    font-size: 0.78rem;
    color: var(--text-faint) !important;
    text-align: center;
    margin-top: 1rem;
    line-height: 1.75;
}
.login-hr {
    border: none;
    border-top: 1px solid var(--border);
    margin: 1.25rem 0;
}

/* ═══════════════════════════════════════════
   SIDEBAR TYPOGRAPHY
   ═══════════════════════════════════════════ */
.sb-clinic-name { font-size: 1rem; font-weight: 700; color: #e2e8f0 !important; margin-top: .3rem; }
.sb-mono        { font-family: 'DM Mono', monospace; font-size: 0.75rem; color: var(--sb-muted) !important; }
.sb-session     { font-size: 0.72rem; color: var(--sb-muted) !important; line-height: 1.75; }
.sb-footer      { font-size: 0.7rem;  color: var(--sb-muted) !important; margin-top: 1.5rem; line-height: 1.65; }

/* ═══════════════════════════════════════════
   HIDE STREAMLIT CHROME
   ═══════════════════════════════════════════ */
#MainMenu, footer, header { visibility: hidden; }
</style>
""",
    unsafe_allow_html=True,
)


# ──────────────────────────────────────────────
# Dark-mode detection
# We inject a tiny JS snippet once that reads
# prefers-color-scheme and sets a query param
# ?dark=1|0.  On the next rerender Streamlit
# picks it up and we store it in session_state.
# All Plotly calls read st.session_state._dark.
# ──────────────────────────────────────────────
if "_dark_detected" not in st.session_state:
    st.session_state["_dark_detected"] = False
    st.session_state["_dark"] = False

_qp = st.query_params
if "dark" in _qp and not st.session_state["_dark_detected"]:
    st.session_state["_dark"] = _qp["dark"] == "1"
    st.session_state["_dark_detected"] = True

if not st.session_state["_dark_detected"]:
    st.components.v1.html(
        """
    <script>
    (function() {
        var dark = window.matchMedia('(prefers-color-scheme: dark)').matches ? '1' : '0';
        var url  = new URL(window.parent.location.href);
        url.searchParams.set('dark', dark);
        window.parent.history.replaceState({}, '', url.toString());
        // Force Streamlit to rerun by patching location
        window.parent.dispatchEvent(new Event('popstate'));
    })();
    </script>
    """,
        height=0,
    )


def is_dark() -> bool:
    return st.session_state.get("_dark", False)


def plotly_theme(height: int = 300) -> dict:
    """Adaptive Plotly layout dict."""
    dark = is_dark()
    bg = "#1e293b" if dark else "#ffffff"
    grid = "#334155" if dark else "#f1f5f9"
    fc = "#94a3b8" if dark else "#334155"
    return dict(
        plot_bgcolor=bg,
        paper_bgcolor=bg,
        margin=dict(l=0, r=0, t=10, b=0),
        font=dict(family="DM Sans", color=fc, size=12),
        xaxis=dict(showgrid=False, color=fc, linecolor=grid, tickfont=dict(color=fc)),
        yaxis=dict(
            showgrid=True,
            gridcolor=grid,
            color=fc,
            linecolor=grid,
            tickfont=dict(color=fc),
        ),
        legend=dict(font=dict(color=fc, size=11)),
        height=height,
    )


def chart_colors() -> dict:
    """Return adaptive chart colour tokens."""
    dark = is_dark()
    return dict(
        primary="#60a5fa" if dark else "#2563eb",
        secondary="#3b82f6" if dark else "#1e3a5f",
        fill="rgba(96,165,250,0.12)" if dark else "rgba(37,99,235,0.10)",
        scale=(
            ["#1e3a5f", "#2563eb", "#60a5fa", "#bfdbfe"]
            if not dark
            else ["#172033", "#1e3a5f", "#3b82f6", "#93c5fd"]
        ),
        pie=(
            [
                "#1e3a5f",
                "#2563eb",
                "#3b82f6",
                "#60a5fa",
                "#93c5fd",
                "#bfdbfe",
                "#dbeafe",
                "#eff6ff",
            ]
            if not dark
            else [
                "#93c5fd",
                "#60a5fa",
                "#3b82f6",
                "#2563eb",
                "#1d4ed8",
                "#1e40af",
                "#1e3a5f",
                "#172033",
            ]
        ),
    )


# ──────────────────────────────────────────────
# Security Helpers
# ──────────────────────────────────────────────
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


def _rate_key(clinic_id: str) -> str:
    return f"_rate_{clinic_id}"


def check_rate_limit(clinic_id: str) -> tuple[bool, str]:
    key = _rate_key(clinic_id)
    now = datetime.utcnow()
    record = st.session_state.get(key, {"attempts": 0, "locked_until": None})
    if record["locked_until"] and now < record["locked_until"]:
        remaining = int((record["locked_until"] - now).total_seconds() // 60) + 1
        return False, f"Too many failed attempts. Try again in {remaining} minute(s)."
    return True, ""


def record_failed_attempt(clinic_id: str):
    key = _rate_key(clinic_id)
    record = st.session_state.get(key, {"attempts": 0, "locked_until": None})
    record["attempts"] += 1
    if record["attempts"] >= MAX_LOGIN_ATTEMPTS:
        record["locked_until"] = datetime.utcnow() + timedelta(minutes=LOCKOUT_MINUTES)
        logger.warning("Account locked clinic_id=%s", clinic_id)
    st.session_state[key] = record


def clear_rate_limit(clinic_id: str):
    st.session_state.pop(_rate_key(clinic_id), None)


def sanitize(value: str, max_len: int = 500) -> str:
    return value.strip()[:max_len]


# ──────────────────────────────────────────────
# Database
# ──────────────────────────────────────────────
# Session State
_DEFAULTS = {
    "authenticated": False,
    "tenant_id": None,
    "clinic_name": None,
    "api_key": None,
    "session_token": None,
    "session_created": None,
}
for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


SESSION_LIFETIME_HOURS = int(os.getenv("SESSION_LIFETIME_HOURS", "8"))


def create_session(clinic_id: str, clinic_name: str, api_key: str):
    st.session_state.update(
        {
            "authenticated": True,
            "tenant_id": clinic_id,
            "clinic_name": clinic_name,
            "api_key": api_key,
            "session_token": secrets.token_hex(32),
            "session_created": datetime.utcnow(),
        }
    )
    logger.info("Session started clinic_id=%s", clinic_id)


def destroy_session():
    logger.info("Session ended clinic_id=%s", st.session_state.tenant_id)
    for k, v in _DEFAULTS.items():
        st.session_state[k] = v


def validate_session() -> bool:
    if not st.session_state.authenticated or not st.session_state.session_created:
        return False
    if datetime.utcnow() - st.session_state.session_created > timedelta(
        hours=SESSION_LIFETIME_HOURS
    ):
        destroy_session()
        st.warning("⏱️ Session expired. Please log in again.")
        return False
    return True


def verify_credentials(clinic_id: str, api_key: str) -> tuple[bool, str | None]:
    try:
        verified_id, clinic_name = tenant_verify_credentials(
            sanitize(clinic_id, 64), api_key
        )
        return verified_id == sanitize(clinic_id, 64), clinic_name
    except APIError as exc:
        logger.error("Credential error: %s", exc)
        return False, None


# Tenant-scoped DB helpers
def tid() -> str:
    return st.session_state.tenant_id


def get_appointments():
    return tenant_get_appointments(st.session_state.api_key)


def get_settings():
    return tenant_get_settings(st.session_state.api_key)


def get_working_hours():
    return tenant_get_working_hours(st.session_state.api_key)


def get_clinic():
    return tenant_get_clinic(st.session_state.api_key)


# LOGIN PAGE
# ══════════════════════════════════════════════
if not validate_session():
    st.markdown(
        """
    <div class="login-hero">
        <div style="font-size:2.6rem;">🏥</div>
        <h1>Clinic AI Receptionist</h1>
        <p>Secure multi-tenant portal</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    _, col_mid, _ = st.columns([1, 1.1, 1])
    with col_mid:
        st.markdown("#### Sign in to your clinic")
        clinic_id_in = st.text_input(
            "Clinic ID", placeholder="e.g. clinic_abc123", max_chars=64
        )
        api_key_in = st.text_input(
            "API Key", type="password", placeholder="••••••••••••••••", max_chars=256
        )
        login_btn = st.button("Sign In →", use_container_width=True, type="primary")

        if login_btn:
            if not clinic_id_in or not api_key_in:
                st.error("Please enter both Clinic ID and API Key.")
            else:
                c_id = sanitize(clinic_id_in, 64)
                allowed, rate_msg = check_rate_limit(c_id)
                if not allowed:
                    st.error(f"🔒 {rate_msg}")
                else:
                    ok, name = verify_credentials(c_id, api_key_in)
                    if ok:
                        clear_rate_limit(c_id)
                        create_session(c_id, name, api_key_in)
                        st.rerun()
                    else:
                        record_failed_attempt(c_id)
                        attempts = st.session_state.get(_rate_key(c_id), {}).get(
                            "attempts", 0
                        )
                        left = max(MAX_LOGIN_ATTEMPTS - attempts, 0)
                        st.error(
                            f"❌ Invalid credentials. {left} attempt(s) remaining."
                        )

        st.markdown('<hr class="login-hr">', unsafe_allow_html=True)
        st.markdown(
            """
        <p class="login-footer">
            No credentials? Contact your system administrator.<br>
            Sessions expire automatically after 8 hours.
        </p>
        """,
            unsafe_allow_html=True,
        )

    st.stop()


# ══════════════════════════════════════════════
# AUTHENTICATED — SIDEBAR
# ══════════════════════════════════════════════
with st.sidebar:
    st.markdown(
        f"""
    <div style="padding:.5rem 0 1rem;">
        <div style="font-size:1.5rem; line-height:1;">🏥</div>
        <div class="sb-clinic-name">{st.session_state.clinic_name}</div>
        <div class="sb-mono">ID: {tid()}</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.divider()

    menu = st.radio(
        "Navigation",
        [
            "📊 Dashboard",
            "📅 Appointments",
            "📈 Analytics",
            "⏰ Working Hours",
            "⚙️ Settings",
        ],
        label_visibility="collapsed",
    )

    st.divider()

    _age = datetime.utcnow() - st.session_state.session_created
    _a_hrs = _age.seconds // 3600
    _a_min = (_age.seconds % 3600) // 60
    _exp = max(SESSION_LIFETIME_HOURS - _a_hrs, 0)
    st.markdown(
        f"""
    <div class="sb-session">
        🕐 Active {_a_hrs}h {_a_min}m &nbsp;·&nbsp; Expires in {_exp}h
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Sign Out", use_container_width=True):
        destroy_session()
        st.rerun()

    st.markdown(
        """
    <div class="sb-footer">
        AI Receptionist Platform<br>© 2026 · All rights reserved
    </div>
    """,
        unsafe_allow_html=True,
    )


# ──────────────────────────────────────────────
# Shared UI helpers
# ──────────────────────────────────────────────
def page_header(icon: str, title: str, subtitle: str = ""):
    sub = f'<div class="ph-sub">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f"""
    <div class="ph">
        <div class="ph-icon">{icon}</div>
        <div><div class="ph-title">{title}</div>{sub}</div>
    </div>
    """,
        unsafe_allow_html=True,
    )


def notice(text: str, kind: str = "warning"):
    """Render a themed notice box that adapts to dark/light mode."""
    st.markdown(
        f'<div class="notice notice-{kind}">{text}</div>', unsafe_allow_html=True
    )


# ══════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════
if menu == "📊 Dashboard":
    page_header("📊", "Dashboard", f"Welcome back, {st.session_state.clinic_name}")

    appointments = get_appointments()
    settings = get_settings()
    today_str = date.today().isoformat()
    today_appts = [a for a in appointments if a.date == today_str]
    upcoming_appts = [a for a in appointments if a.date > today_str]
    past_appts = [a for a in appointments if a.date < today_str]

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Appointments", len(appointments))
    c2.metric("Today", len(today_appts))
    c3.metric("Upcoming", len(upcoming_appts))
    c4.metric("Past", len(past_appts))
    c5.metric(
        "Appt. Duration", f"{settings.appointment_duration if settings else 30} min"
    )

    st.divider()

    col_l, col_r = st.columns([3, 2])
    with col_l:
        st.subheader("Today's Schedule")
        if today_appts:
            df = pd.DataFrame(
                [
                    {
                        "Time": a.time,
                        "Patient": a.name,
                        "Phone": a.phone,
                        "Reason": a.reason or "—",
                    }
                    for a in sorted(today_appts, key=lambda x: x.time)
                ]
            )
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No appointments scheduled for today.")

    with col_r:
        st.subheader("Next 5 Upcoming")
        if upcoming_appts:
            df_up = pd.DataFrame(
                [
                    {
                        "Date": a.date,
                        "Time": a.time,
                        "Patient": a.name,
                    }
                    for a in upcoming_appts[:5]
                ]
            )
            st.dataframe(df_up, use_container_width=True, hide_index=True)
        else:
            st.info("No upcoming appointments.")

    st.divider()

    if appointments:
        st.subheader("Appointments — Last 30 Days")
        cutoff = (date.today() - timedelta(days=30)).isoformat()
        recent = [a for a in appointments if a.date >= cutoff]
        if recent:
            cc = chart_colors()
            df_r = pd.DataFrame({"date": pd.to_datetime([a.date for a in recent])})
            df_r = df_r.groupby(df_r["date"].dt.date).size().reset_index(name="count")
            fig = px.bar(
                df_r,
                x="date",
                y="count",
                labels={"date": "Date", "count": "Appointments"},
                color_discrete_sequence=[cc["secondary"]],
            )
            fig.update_layout(**plotly_theme(260))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No appointments in the last 30 days.")


# ══════════════════════════════════════════════
# APPOINTMENTS
# ══════════════════════════════════════════════
elif menu == "📅 Appointments":
    page_header("📅", "Appointments", "Manage patient bookings")

    appointments = get_appointments()

    with st.expander("➕ Add New Appointment", expanded=False):
        with st.form("new_appt_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                p_name = st.text_input("Patient Name *", max_chars=120)
                p_phone = st.text_input("Phone Number *", max_chars=30)
                p_date = st.date_input("Date *", min_value=date.today())
            with c2:
                p_time = st.time_input("Time *", value=time(9, 0), step=900)
                p_reason = st.text_area("Reason for Visit", max_chars=500, height=100)

            if st.form_submit_button(
                "Create Appointment", type="primary", use_container_width=True
            ):
                if not p_name.strip() or not p_phone.strip():
                    st.error("Patient name and phone are required.")
                else:
                    try:
                        tenant_create_appointment(
                            st.session_state.api_key,
                            sanitize(p_name),
                            sanitize(p_phone, 30),
                            str(p_date),
                            str(p_time)[:5],
                            sanitize(p_reason),
                        )
                        logger.info("Appointment created tenant=%s", tid())
                        st.success("✅ Appointment created.")
                        st.rerun()
                    except Exception as exc:
                        logger.error("Create appt failed: %s", exc)
                        st.error("Failed to save. Please try again.")

    st.divider()

    # Filters
    cf1, cf2, cf3 = st.columns(3)
    with cf1:
        date_filter = st.selectbox(
            "Filter by", ["All", "Today", "This Week", "This Month", "Past"]
        )
    with cf2:
        search_term = st.text_input(
            "Search name / phone", placeholder="Type to search…"
        )
    with cf3:
        sort_by = st.selectbox(
            "Sort by", ["Date & Time ↑", "Date & Time ↓", "Patient Name"]
        )

    today_s = date.today().isoformat()
    week_end = (date.today() + timedelta(days=7)).isoformat()
    month_end = (date.today() + timedelta(days=30)).isoformat()

    filtered = appointments
    if date_filter == "Today":
        filtered = [a for a in filtered if a.date == today_s]
    elif date_filter == "This Week":
        filtered = [a for a in filtered if today_s <= a.date <= week_end]
    elif date_filter == "This Month":
        filtered = [a for a in filtered if today_s <= a.date <= month_end]
    elif date_filter == "Past":
        filtered = [a for a in filtered if a.date < today_s]

    if search_term.strip():
        s = search_term.strip().lower()
        filtered = [
            a for a in filtered if s in a.name.lower() or s in (a.phone or "").lower()
        ]

    if sort_by == "Date & Time ↓":
        filtered = sorted(filtered, key=lambda x: (x.date, x.time), reverse=True)
    elif sort_by == "Patient Name":
        filtered = sorted(filtered, key=lambda x: x.name.lower())
    else:
        filtered = sorted(filtered, key=lambda x: (x.date, x.time))

    st.subheader(f"Appointments ({len(filtered)} found)")
    if filtered:
        df = pd.DataFrame(
            [
                {
                    "ID": a.id,
                    "Patient": a.name,
                    "Phone": a.phone,
                    "Date": a.date,
                    "Time": a.time,
                    "Reason": (a.reason or "—")[:60],
                }
                for a in filtered
            ]
        )
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No appointments match your filters.")

    if appointments:
        st.divider()
        st.subheader("✏️ Edit or Cancel Appointment")
        appt_opts = {
            a.id: f"#{a.id} — {a.name} ({a.date} {a.time})" for a in appointments
        }
        sel_id = st.selectbox(
            "Select appointment",
            list(appt_opts.keys()),
            format_func=lambda x: appt_opts[x],
        )

        if sel_id:
            appt = tenant_get_appointment(st.session_state.api_key, sel_id)

            if not appt:
                st.error("Appointment not found or access denied.")
            else:
                with st.form("edit_appt_form"):
                    e1, e2 = st.columns(2)
                    with e1:
                        e_name = st.text_input(
                            "Patient Name", value=appt.name, max_chars=120
                        )
                        e_phone = st.text_input("Phone", value=appt.phone, max_chars=30)
                        e_date = st.text_input(
                            "Date (YYYY-MM-DD)", value=appt.date, max_chars=10
                        )
                    with e2:
                        e_time = st.text_input(
                            "Time (HH:MM)", value=appt.time, max_chars=5
                        )
                        e_reason = st.text_area(
                            "Reason", value=appt.reason or "", max_chars=500, height=100
                        )

                    su, sd = st.columns(2)
                    with su:
                        save_btn = st.form_submit_button(
                            "💾 Save Changes", use_container_width=True, type="primary"
                        )
                    with sd:
                        delete_btn = st.form_submit_button(
                            "🗑️ Cancel Appointment", use_container_width=True
                        )

                    if save_btn:
                        try:
                            tenant_update_appointment(
                                st.session_state.api_key,
                                sel_id,
                                sanitize(e_name),
                                sanitize(e_phone, 30),
                                sanitize(e_date, 10),
                                sanitize(e_time, 5),
                                sanitize(e_reason),
                            )
                            st.success("✅ Appointment updated.")
                            st.rerun()
                        except Exception as exc:
                            logger.error("Update appt %s: %s", sel_id, exc)
                            st.error("Update failed. Please try again.")

                    if delete_btn:
                        try:
                            tenant_delete_appointment(st.session_state.api_key, sel_id)
                            logger.info("Appt %s deleted tenant=%s", sel_id, tid())
                            st.success("✅ Appointment cancelled.")
                            st.rerun()
                        except Exception as exc:
                            logger.error("Delete appt %s: %s", sel_id, exc)
                            st.error("Delete failed. Please try again.")


# ══════════════════════════════════════════════
# ANALYTICS
# ══════════════════════════════════════════════
elif menu == "📈 Analytics":
    page_header("📈", "Analytics", "Insights into your clinic's appointment patterns")

    appointments = get_appointments()
    cc = chart_colors()

    if not appointments:
        st.info(
            "No appointment data yet. Analytics will appear once bookings are recorded."
        )
        st.stop()

    df_all = pd.DataFrame(
        [
            {
                "date": a.date,
                "time": a.time,
                "name": a.name,
                "phone": a.phone,
                "reason": a.reason or "Unspecified",
            }
            for a in appointments
        ]
    )

    df_all["date"] = pd.to_datetime(df_all["date"])
    df_all["month"] = df_all["date"].dt.to_period("M").astype(str)
    df_all["weekday"] = df_all["date"].dt.day_name()
    df_all["hour"] = pd.to_numeric(df_all["time"].str[:2], errors="coerce")

    r1, _ = st.columns(2)
    with r1:
        range_opt = st.selectbox(
            "Date Range", ["Last 30 days", "Last 90 days", "Last 12 months", "All time"]
        )

    cutoff_map = {
        "Last 30 days": date.today() - timedelta(days=30),
        "Last 90 days": date.today() - timedelta(days=90),
        "Last 12 months": date.today() - timedelta(days=365),
        "All time": date(2000, 1, 1),
    }
    cutoff = pd.Timestamp(cutoff_map[range_opt])
    df = df_all[df_all["date"] >= cutoff].copy()

    if df.empty:
        st.warning("No data in the selected range.")
        st.stop()

    busiest_day = df.groupby("weekday").size().idxmax()
    unique_pts = df["phone"].nunique()
    span_days = max((df["date"].max() - df["date"].min()).days, 1)
    avg_per_week = round(len(df) / max(span_days / 7, 1), 1)

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Appointments", len(df))
    k2.metric("Unique Patients", unique_pts)
    k3.metric("Avg / Week", avg_per_week)
    k4.metric("Busiest Day", busiest_day)

    st.divider()

    # Row 1 — Volume + Weekday
    r1c1, r1c2 = st.columns([2, 1])

    with r1c1:
        st.subheader("Volume Over Time")
        freq = "D" if range_opt == "Last 30 days" else "W"
        df_vol = (
            df.groupby(df["date"].dt.to_period(freq).dt.start_time)
            .size()
            .reset_index(name="count")
        )
        fig_vol = px.area(
            df_vol,
            x="date",
            y="count",
            labels={"date": "", "count": "Appointments"},
            color_discrete_sequence=[cc["primary"]],
        )
        fig_vol.update_traces(line_color=cc["primary"], fillcolor=cc["fill"])
        fig_vol.update_layout(**plotly_theme(280))
        st.plotly_chart(fig_vol, use_container_width=True)

    with r1c2:
        st.subheader("By Day of Week")
        day_order = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
        df_wd = (
            df.groupby("weekday")
            .size()
            .reindex(day_order, fill_value=0)
            .reset_index(name="count")
        )
        df_wd.columns = ["day", "count"]
        fig_wd = px.bar(
            df_wd,
            x="count",
            y="day",
            orientation="h",
            color="count",
            color_continuous_scale=cc["scale"],
            labels={"count": "Appts", "day": ""},
        )
        lay_wd = plotly_theme(280)
        lay_wd["yaxis"]["categoryorder"] = "array"
        lay_wd["yaxis"]["categoryarray"] = day_order[::-1]
        fig_wd.update_layout(**lay_wd, coloraxis_showscale=False)
        st.plotly_chart(fig_wd, use_container_width=True)

    # Row 2 — Hour distribution + Top reasons
    r2c1, r2c2 = st.columns(2)

    with r2c1:
        st.subheader("Time of Day")
        hour_df = df["hour"].dropna().value_counts().sort_index().reset_index()
        hour_df.columns = ["hour", "count"]
        hour_df["label"] = hour_df["hour"].apply(lambda h: f"{int(h):02d}:00")
        fig_hr = px.bar(
            hour_df,
            x="label",
            y="count",
            labels={"label": "Hour", "count": "Appointments"},
            color_discrete_sequence=[cc["secondary"]],
        )
        fig_hr.update_layout(**plotly_theme(260))
        st.plotly_chart(fig_hr, use_container_width=True)

    with r2c2:
        st.subheader("Top Visit Reasons")
        rc = df["reason"].value_counts().head(8).reset_index()
        rc.columns = ["reason", "count"]
        fig_pie = px.pie(
            rc,
            names="reason",
            values="count",
            hole=0.55,
            color_discrete_sequence=cc["pie"],
        )
        lay_pie = plotly_theme(260)
        lay_pie.pop("xaxis", None)
        lay_pie.pop("yaxis", None)
        fig_pie.update_layout(**lay_pie)
        st.plotly_chart(fig_pie, use_container_width=True)

    st.divider()
    st.subheader("Monthly Summary")
    df_mo = df.groupby("month").size().reset_index(name="Appointments")
    df_mo.columns = ["Month", "Appointments"]
    st.dataframe(
        df_mo.sort_values("Month", ascending=False),
        use_container_width=True,
        hide_index=True,
    )


# ══════════════════════════════════════════════
# WORKING HOURS
# ══════════════════════════════════════════════
elif menu == "⏰ Working Hours":
    page_header("⏰", "Working Hours", "Configure your clinic's operating schedule")

    DAYS = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    current_hrs = get_working_hours()
    hours_map = {wh.day_of_week: wh for wh in current_hrs}

    st.subheader("Weekly Schedule")
    st.caption("Enable days and set opening/closing times. Click Save when done.")

    updated = []
    for day_num, day_name in enumerate(DAYS):
        c1, c2, c3 = st.columns([2, 3, 3])
        with c1:
            enabled = st.checkbox(
                day_name, value=(day_num in hours_map), key=f"en_{day_num}"
            )
        with c2:
            s_val = (
                hours_map[day_num].start_time if day_num in hours_map else time(9, 0)
            )
            s = st.time_input(
                "Opens", value=s_val, key=f"s_{day_num}", disabled=not enabled
            )
        with c3:
            e_val = hours_map[day_num].end_time if day_num in hours_map else time(17, 0)
            e = st.time_input(
                "Closes", value=e_val, key=f"e_{day_num}", disabled=not enabled
            )
        if enabled:
            updated.append((day_num, s, e))

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("💾 Save Working Hours", type="primary", use_container_width=True):
        try:
            tenant_update_working_hours(st.session_state.api_key, updated)
            logger.info("Working hours saved tenant=%s", tid())
            st.success("✅ Working hours saved.")
            st.rerun()
        except Exception as exc:
            logger.error("Save working hours: %s", exc)
            st.error("Save failed. Please try again.")


# ══════════════════════════════════════════════
# SETTINGS
# ══════════════════════════════════════════════
elif menu == "⚙️ Settings":
    page_header("⚙️", "Settings", "Clinic configuration and account details")

    settings = get_settings()
    clinic = get_clinic()

    if not clinic:
        st.error("Could not load clinic data.")
        st.stop()

    st.subheader("Clinic Information")
    c1, c2 = st.columns(2)
    with c1:
        st.text_input("Clinic ID", value=clinic.id, disabled=True)
        st.text_input("Clinic Name", value=clinic.name, disabled=True)
    with c2:
        st.text_input(
            "API Key",
            value="••••••••••••••••",
            disabled=True,
            help="Contact admin to rotate your API key.",
        )
        st.text_input(
            "Timezone", value=settings.timezone if settings else "UTC", disabled=True
        )

    notice(
        "🔑 To rotate your API key or rename your clinic, contact your system administrator.",
        "warning",
    )

    st.divider()
    st.subheader("Appointment Settings")

    if settings:
        new_dur = st.number_input(
            "Default Appointment Duration (minutes)",
            min_value=10,
            max_value=240,
            value=settings.appointment_duration,
            step=5,
            help="Used by the AI Receptionist when scheduling bookings.",
        )
        if st.button("💾 Save Settings", type="primary"):
            try:
                tenant_update_settings(st.session_state.api_key, new_dur)
                logger.info("Settings saved tenant=%s dur=%s", tid(), new_dur)
                st.success("✅ Settings saved.")
                st.rerun()
            except Exception as exc:
                logger.error("Save settings: %s", exc)
                st.error("Save failed. Please try again.")
    else:
        st.warning("No settings record found. Contact your administrator.")

    st.divider()
    st.subheader("Session & Security")
    sc1, sc2 = st.columns(2)
    with sc1:
        if st.button("🔓 Sign Out", use_container_width=True):
            destroy_session()
            st.rerun()
    with sc2:
        created_str = (
            st.session_state.session_created.strftime("%Y-%m-%d %H:%M")
            if st.session_state.session_created
            else "—"
        )
        st.markdown(
            f'<div class="session-box">Session started: {created_str} UTC</div>',
            unsafe_allow_html=True,
        )

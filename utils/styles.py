import streamlit as st

def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

    /* Font Family Settings */
    html, body, [class*="css"], .stApp {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }

    /* Force Light Slate/Blue Background on all Streamlit main containers */
    .stApp, 
    [data-testid="stAppViewContainer"], 
    [data-testid="stMainViewContainer"],
    [data-testid="stMain"],
    [data-testid="stHeader"] {
        background-color: #f1f5f9 !important;
        background-image: none !important;
        color: #1e293b !important;
    }

    /* Force Sidebar Background - Pure White with right border */
    [data-testid="stSidebar"], 
    [data-testid="stSidebar"] > div {
        background-color: #ffffff !important;
        border-right: 1px solid #e2e8f0 !important;
    }

    /* Sidebar Headings and Labels - Dark Slate */
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stFileUploader label,
    [data-testid="stSidebar"] .stRadio label,
    [data-testid="stSidebar"] .stTextInput label,
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #334155 !important;
        font-size: 0.85rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.05em !important;
        text-transform: uppercase !important;
        margin-bottom: 6px !important;
    }

    /* Premium Header Container - Pure White Card with gray border and shadow */
    .header-container {
        padding: 2rem;
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
        margin-bottom: 2rem;
    }
    
    /* Bold Charcoal Title */
    .main-title {
        font-size: 2.5rem;
        font-weight: 800;
        color: #0f172a !important; /* Dark Slate */
        letter-spacing: -0.02em;
        margin-bottom: 0.5rem;
    }
    
    /* Muted Slate Subtitle */
    .sub-title {
        font-size: 1rem;
        font-weight: 400;
        color: #64748b !important; /* Muted blue-gray */
    }

    /* KPI Cards Container styling - Pure White base */
    .metric-card {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 12px;
        padding: 1.25rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
        transition: all 0.2s ease-in-out;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.08);
        border-color: #cbd5e1 !important;
    }

    .metric-title {
        font-size: 0.8rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #64748b;
        margin-bottom: 0.3rem;
    }
    
    .metric-value {
        font-size: 2rem;
        font-weight: 800;
        font-family: 'JetBrains Mono', monospace;
        letter-spacing: -0.01em;
    }

    /* Left-border colored indicators */
    .metric-total {
        border-left: 4px solid #2563eb !important; /* Royal Blue */
    }
    .metric-total .metric-value {
        color: #1d4ed8 !important;
    }

    .metric-passed {
        border-left: 4px solid #10b981 !important; /* Emerald */
    }
    .metric-passed .metric-value {
        color: #047857 !important;
    }

    .metric-warnings {
        border-left: 4px solid #f59e0b !important; /* Amber */
    }
    .metric-warnings .metric-value {
        color: #b45309 !important;
    }

    .metric-failed {
        border-left: 4px solid #ef4444 !important; /* Red */
    }
    .metric-failed .metric-value {
        color: #b91c1c !important;
    }

    /* Tabs Component Styling - White backdrop with royal blue underline style */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #ffffff !important;
        border-radius: 8px;
        padding: 4px;
        border: 1px solid #e2e8f0 !important;
        gap: 4px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
    }
    .stTabs [data-baseweb="tab"] {
        color: #64748b !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        padding: 8px 16px !important;
        border-radius: 6px !important;
        border: none !important;
        transition: all 0.15s;
    }
    .stTabs [aria-selected="true"] {
        color: #2563eb !important; /* Royal Blue text */
        background-color: #f8fafc !important; /* Very soft light gray */
        border-bottom: 2px solid #2563eb !important;
        font-weight: 700 !important;
    }

    /* Custom buttons (primary & download) */
    .stButton > button {
        border-radius: 8px !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        letter-spacing: 0.01em !important;
        transition: all 0.2s ease-in-out !important;
        padding: 0.5rem 1.5rem !important;
    }
    .stButton > button[kind="primary"] {
        background-color: #2563eb !important; /* Royal Blue */
        color: white !important;
        border: 1px solid #1d4ed8 !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1) !important;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #1d4ed8 !important;
        transform: translateY(-0.5px) !important;
        box-shadow: 0 4px 6px rgba(37, 99, 235, 0.15) !important;
    }

    .stDownloadButton > button {
        background-color: #0f766e !important;
        border: 1px solid #0d9488 !important;
        color: #ffffff !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1) !important;
    }
    .stDownloadButton > button:hover {
        background-color: #0d9488 !important;
        transform: translateY(-0.5px) !important;
        box-shadow: 0 4px 6px rgba(13, 148, 136, 0.15) !important;
    }

    /* Expanders & details panels */
    .streamlit-expanderHeader {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 8px !important;
        font-size: 0.9rem !important;
        font-weight: 600 !important;
        color: #1e293b !important;
        margin-bottom: 0.4rem !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.02) !important;
    }
    .streamlit-expanderContent {
        border-left: 1px solid #e2e8f0 !important;
        border-right: 1px solid #e2e8f0 !important;
        border-bottom: 1px solid #e2e8f0 !important;
        background-color: #ffffff !important;
        padding: 1.25rem !important;
        border-radius: 0 0 8px 8px !important;
    }

    /* Input selectbox and text areas formatting */
    div[data-baseweb="select"] {
        background-color: #ffffff !important;
        border-radius: 8px !important;
        border: 1px solid #cbd5e1 !important;
    }

    /* Logs view block */
    .log-box {
        font-family: 'JetBrains Mono', monospace !important;
        background-color: #0f172a !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 8px !important;
        padding: 1rem !important;
        height: 250px !important;
        overflow-y: auto !important;
        color: #38bdf8 !important;
        font-size: 0.85rem !important;
        line-height: 1.5 !important;
        box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.3) !important;
    }

    /* Notification alert boxes */
    div[data-testid="stNotification"] {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        color: #1e293b !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02) !important;
    }

    /* Soft pill badges */
    .qc-error-badge {
        background-color: #fee2e2 !important;
        color: #991b1b !important;
        padding: 3px 10px !important;
        border-radius: 12px !important;
        font-size: 0.72rem !important;
        font-weight: 700 !important;
        display: inline-block !important;
        border: 1px solid #fca5a5 !important;
    }
    .qc-warn-badge {
        background-color: #fef3c7 !important;
        color: #92400e !important;
        padding: 3px 10px !important;
        border-radius: 12px !important;
        font-size: 0.72rem !important;
        font-weight: 700 !important;
        display: inline-block !important;
        border: 1px solid #fde047 !important;
    }
    .qc-pass-badge {
        background-color: #d1fae5 !important;
        color: #065f46 !important;
        padding: 3px 10px !important;
        border-radius: 12px !important;
        font-size: 0.72rem !important;
        font-weight: 700 !important;
        display: inline-block !important;
        border: 1px solid #6ee7b7 !important;
    }

    </style>
    """, unsafe_allow_html=True)

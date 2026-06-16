import streamlit as st

def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .stApp {
        background: #0d0f14;
        color: #e2e8f0;
    }

    /* Header Styling */
    .header-container {
        padding: 1.5rem 0;
        margin-bottom: 2rem;
        border-bottom: 1px solid #1e293b;
    }
    .main-title {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #38bdf8, #818cf8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .sub-title {
        font-size: 1rem;
        color: #94a3b8;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background: #111827;
        border-right: 1px solid #1f2937;
    }
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stFileUploader label,
    section[data-testid="stSidebar"] .stTextInput label,
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #9ca3af !important;
        font-size: 0.8rem;
        font-weight: 600;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }

    /* KPI Cards / Metric Styling */
    .metric-card {
        background: rgba(17, 24, 39, 0.7);
        border: 1px solid #1f2937;
        border-radius: 12px;
        padding: 1.25rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        backdrop-filter: blur(10px);
        margin-bottom: 1rem;
    }
    .metric-title {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #9ca3af;
        margin-bottom: 0.5rem;
    }
    .metric-value {
        font-size: 1.75rem;
        font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
    }
    
    .metric-total .metric-value { color: #38bdf8; }
    .metric-passed .metric-value { color: #34d399; }
    .metric-failed .metric-value { color: #f87171; }
    .metric-warnings .metric-value { color: #fbbf24; }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        background: #111827;
        border-radius: 8px;
        padding: 6px;
        border: 1px solid #1f2937;
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        color: #9ca3af;
        font-weight: 500;
        font-size: 0.85rem;
        padding: 8px 16px;
        border-radius: 6px;
        border: none;
    }
    .stTabs [aria-selected="true"] {
        color: #ffffff !important;
        background: #1f2937 !important;
        font-weight: 600;
    }

    /* Form Buttons */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        letter-spacing: 0.025em;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #0ea5e9, #4f46e5);
        color: white;
        border: none;
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #38bdf8, #6366f1);
        transform: translateY(-1px);
        box-shadow: 0 4px 14px rgba(99, 102, 241, 0.4);
    }
    .stDownloadButton > button {
        background: #065f46;
        border: 1px solid #059669;
        color: #d1fae5;
    }
    .stDownloadButton > button:hover {
        background: #047857;
        color: white;
        border-color: #10b981;
    }

    /* Expander / Details */
    .streamlit-expanderHeader {
        background-color: #111827 !important;
        border: 1px solid #1f2937 !important;
        border-radius: 8px !important;
        font-size: 0.85rem !important;
        font-weight: 500;
        color: #d1d5db !important;
        margin-bottom: 0.5rem;
    }
    .streamlit-expanderContent {
        border-left: 1px solid #1f2937 !important;
        border-right: 1px solid #1f2937 !important;
        border-bottom: 1px solid #1f2937 !important;
        background-color: #0f172a;
        padding: 1rem !important;
    }

    /* Logs & Terminal output box */
    .log-box {
        font-family: 'JetBrains Mono', monospace;
        background: #030712;
        border: 1px solid #1f2937;
        border-radius: 8px;
        padding: 1rem;
        height: 250px;
        overflow-y: auto;
        color: #10b981;
        font-size: 0.85rem;
        line-height: 1.5;
        margin-bottom: 1rem;
    }

    /* Error and Warning tables styling */
    .qc-error-badge {
        background-color: #7f1d1d;
        color: #fca5a5;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
    }
    .qc-warn-badge {
        background-color: #78350f;
        color: #fde047;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
    }
    .qc-pass-badge {
        background-color: #064e3b;
        color: #6ee7b7;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
    }

    </style>
    """, unsafe_allow_html=True)

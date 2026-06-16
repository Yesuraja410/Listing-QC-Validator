import streamlit as st

def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

    /* Font Family Settings */
    html, body, [class*="css"], .stApp {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }

    /* Force Sleek Charcoal Background on all Streamlit containers */
    .stApp, 
    [data-testid="stAppViewContainer"], 
    [data-testid="stMainViewContainer"],
    [data-testid="stMain"],
    [data-testid="stHeader"] {
        background-color: #12131a !important;
        background-image: none !important;
        color: #e2e8f0 !important;
    }

    /* Force Sidebar Background */
    [data-testid="stSidebar"], 
    [data-testid="stSidebar"] > div {
        background-color: #0b0c10 !important;
        border-right: 1px solid rgba(6, 182, 212, 0.15) !important;
    }

    /* Premium Header Container - Crisp Charcoal Card with Cyan glow */
    .header-container {
        padding: 2rem;
        background-color: #1a1b24 !important;
        border: 1px solid rgba(6, 182, 212, 0.25) !important;
        border-radius: 16px;
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.8), 0 0 15px rgba(6, 182, 212, 0.05);
        margin-bottom: 2rem;
    }
    
    /* Crisp White Title */
    .main-title {
        font-size: 2.8rem;
        font-weight: 800;
        color: #ffffff !important;
        letter-spacing: -0.02em;
        margin-bottom: 0.5rem;
        text-shadow: 0 2px 10px rgba(0, 0, 0, 0.5);
    }
    
    /* Muted Silver Subtitle */
    .sub-title {
        font-size: 1.05rem;
        font-weight: 400;
        color: #94a3b8 !important;
        letter-spacing: 0.01em;
    }

    /* Sidebar Headings and Labels - Electric Cyan */
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stFileUploader label,
    [data-testid="stSidebar"] .stRadio label,
    [data-testid="stSidebar"] .stTextInput label,
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #06b6d4 !important; /* Electric Teal */
        font-size: 0.85rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.06em !important;
        text-transform: uppercase !important;
        margin-bottom: 6px !important;
    }

    /* KPI Cards Container styling - Slate/Charcoal base */
    .metric-card {
        background-color: #1a1b24 !important;
        border: 1px solid rgba(255, 255, 255, 0.04) !important;
        border-radius: 12px;
        padding: 1.4rem;
        box-shadow: 0 8px 20px -5px rgba(0, 0, 0, 0.6);
        transition: all 0.25s ease-in-out;
    }
    
    .metric-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 15px 30px -8px rgba(0, 0, 0, 0.7);
        border-color: rgba(6, 182, 212, 0.3) !important;
    }

    .metric-title {
        font-size: 0.8rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #64748b;
        margin-bottom: 0.4rem;
    }
    
    .metric-value {
        font-size: 2.1rem;
        font-weight: 800;
        font-family: 'JetBrains Mono', monospace;
        letter-spacing: -0.02em;
    }

    /* Theme colors */
    .metric-total {
        border-left: 4px solid #06b6d4 !important;
    }
    .metric-total .metric-value {
        color: #22d3ee !important; /* Light Teal */
    }

    .metric-passed {
        border-left: 4px solid #10b981 !important;
    }
    .metric-passed .metric-value {
        color: #34d399 !important; /* Mint Green */
    }

    .metric-warnings {
        border-left: 4px solid #f59e0b !important;
    }
    .metric-warnings .metric-value {
        color: #fbbf24 !important; /* Amber */
    }

    .metric-failed {
        border-left: 4px solid #ef4444 !important;
    }
    .metric-failed .metric-value {
        color: #f87171 !important; /* Rose */
    }

    /* Tabs Component Styling */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #0b0c10 !important;
        border-radius: 10px;
        padding: 5px;
        border: 1px solid rgba(6, 182, 212, 0.15) !important;
        gap: 6px;
    }
    .stTabs [data-baseweb="tab"] {
        color: #94a3b8 !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        padding: 8px 16px !important;
        border-radius: 6px !important;
        border: none !important;
        transition: all 0.2s;
    }
    .stTabs [aria-selected="true"] {
        color: #ffffff !important;
        background-color: #0891b2 !important; /* Dark Teal */
        font-weight: 700 !important;
        box-shadow: 0 4px 12px rgba(8, 145, 178, 0.3);
    }

    /* Custom buttons (primary & download) */
    .stButton > button {
        border-radius: 10px !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        letter-spacing: 0.02em !important;
        transition: all 0.25s ease-in-out !important;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #0891b2 0%, #06b6d4 100%) !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 4px 15px rgba(6, 182, 212, 0.25) !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #0e7490 0%, #0891b2 100%) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 20px rgba(6, 182, 212, 0.4) !important;
    }

    .stDownloadButton > button {
        background-color: #0f766e !important;
        border: 1px solid #14b8a6 !important;
        color: #ccfbf1 !important;
        box-shadow: 0 4px 12px rgba(20, 184, 166, 0.15) !important;
    }
    .stDownloadButton > button:hover {
        background-color: #0d9488 !important;
        color: white !important;
        border-color: #2dd4bf !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 18px rgba(20, 184, 166, 0.3) !important;
    }

    /* Expanders & collapse details layout */
    .streamlit-expanderHeader {
        background-color: #1a1b24 !important;
        border: 1px solid rgba(6, 182, 212, 0.15) !important;
        border-radius: 10px !important;
        font-size: 0.9rem !important;
        font-weight: 600 !important;
        color: #ffffff !important;
        margin-bottom: 0.4rem !important;
    }
    .streamlit-expanderContent {
        border-left: 1px solid rgba(6, 182, 212, 0.15) !important;
        border-right: 1px solid rgba(6, 182, 212, 0.15) !important;
        border-bottom: 1px solid rgba(6, 182, 212, 0.15) !important;
        background-color: #0b0c10 !important;
        padding: 1.25rem !important;
        border-radius: 0 0 10px 10px !important;
    }

    /* Logs view block */
    .log-box {
        font-family: 'JetBrains Mono', monospace !important;
        background-color: #050608 !important;
        border: 1px solid rgba(6, 182, 212, 0.2) !important;
        border-radius: 10px !important;
        padding: 1rem !important;
        height: 250px !important;
        overflow-y: auto !important;
        color: #2dd4bf !important;
        font-size: 0.85rem !important;
        line-height: 1.5 !important;
        box-shadow: inset 0 2px 6px rgba(0, 0, 0, 0.7) !important;
    }

    /* Info text boxes in Streamlit */
    div[data-testid="stNotification"] {
        background-color: #1a1b24 !important;
        border: 1px solid rgba(6, 182, 212, 0.2) !important;
        color: #e2e8f0 !important;
        border-radius: 10px !important;
    }

    /* Validation custom badges (pills) */
    .qc-error-badge {
        background-color: #7f1d1d !important;
        color: #fca5a5 !important;
        padding: 3px 8px !important;
        border-radius: 12px !important;
        font-size: 0.72rem !important;
        font-weight: 700 !important;
        display: inline-block !important;
    }
    .qc-warn-badge {
        background-color: #78350f !important;
        color: #fde047 !important;
        padding: 3px 8px !important;
        border-radius: 12px !important;
        font-size: 0.72rem !important;
        font-weight: 700 !important;
        display: inline-block !important;
    }
    .qc-pass-badge {
        background-color: #064e3b !important;
        color: #6ee7b7 !important;
        padding: 3px 8px !important;
        border-radius: 12px !important;
        font-size: 0.72rem !important;
        font-weight: 700 !important;
        display: inline-block !important;
    }

    </style>
    """, unsafe_allow_html=True)

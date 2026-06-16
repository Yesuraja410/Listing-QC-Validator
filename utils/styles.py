import streamlit as st

def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

    /* Font Family Settings */
    html, body, [class*="css"], .stApp {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }

    /* Sleek Deep Teal-Black Background on all Streamlit containers */
    .stApp, 
    [data-testid="stAppViewContainer"], 
    [data-testid="stMainViewContainer"],
    [data-testid="stMain"],
    [data-testid="stHeader"] {
        background-color: #06191d !important;
        background-image: none !important;
        color: #e2e8f0 !important;
    }

    /* Force Sidebar Background - Very Dark Teal */
    [data-testid="stSidebar"], 
    [data-testid="stSidebar"] > div {
        background-color: #030c0e !important;
        border-right: 1px solid rgba(0, 197, 200, 0.15) !important;
    }

    /* Premium Header Container - Teal Slate Card with Turquoise glow */
    .header-container {
        padding: 2rem;
        background-color: #0e282c !important;
        border: 1px solid rgba(0, 197, 200, 0.25) !important;
        border-radius: 16px;
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.9), 0 0 15px rgba(0, 197, 200, 0.05);
        margin-bottom: 2rem;
    }
    
    /* Crisp White Title */
    .main-title {
        font-size: 2.8rem;
        font-weight: 800;
        color: #ffffff !important;
        letter-spacing: -0.02em;
        margin-bottom: 0.5rem;
        text-shadow: 0 0 25px rgba(0, 197, 200, 0.25);
    }
    
    /* Soft Mint Subtitle */
    .sub-title {
        font-size: 1.05rem;
        font-weight: 400;
        color: #70e7d1 !important; /* Mint Teal */
        letter-spacing: 0.01em;
        opacity: 0.9;
    }

    /* Sidebar Headings and Labels - Electric Turquoise */
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stFileUploader label,
    [data-testid="stSidebar"] .stRadio label,
    [data-testid="stSidebar"] .stTextInput label,
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #00c5c8 !important; /* Electric Turquoise */
        font-size: 0.85rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.06em !important;
        text-transform: uppercase !important;
        margin-bottom: 6px !important;
    }

    /* KPI Cards Container styling - Deep Teal Base */
    .metric-card {
        background-color: #0e282c !important;
        border: 1px solid rgba(0, 197, 200, 0.1) !important;
        border-radius: 12px;
        padding: 1.4rem;
        box-shadow: 0 8px 20px -5px rgba(0, 0, 0, 0.7);
        transition: all 0.25s ease-in-out;
    }
    
    .metric-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 15px 30px -8px rgba(0, 0, 0, 0.8);
        border-color: rgba(0, 197, 200, 0.35) !important;
    }

    .metric-title {
        font-size: 0.8rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #70e7d1;
        margin-bottom: 0.4rem;
        opacity: 0.8;
    }
    
    .metric-value {
        font-size: 2.1rem;
        font-weight: 800;
        font-family: 'JetBrains Mono', monospace;
        letter-spacing: -0.02em;
    }

    /* Left-border colored indicators */
    .metric-total {
        border-left: 4px solid #00c5c8 !important; /* Electric Turquoise */
    }
    .metric-total .metric-value {
        color: #70e7d1 !important; /* Mint Teal */
    }

    .metric-passed {
        border-left: 4px solid #10b981 !important; /* Green */
    }
    .metric-passed .metric-value {
        color: #34d399 !important;
    }

    .metric-warnings {
        border-left: 4px solid #f59e0b !important; /* Amber */
    }
    .metric-warnings .metric-value {
        color: #fbbf24 !important;
    }

    .metric-failed {
        border-left: 4px solid #ef4444 !important; /* Red */
    }
    .metric-failed .metric-value {
        color: #f87171 !important;
    }

    /* Tabs Component Styling - Deep Teal Backdrop with Turquoise active selection */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #030c0e !important;
        border-radius: 10px;
        padding: 5px;
        border: 1px solid rgba(0, 197, 200, 0.15) !important;
        gap: 6px;
    }
    .stTabs [data-baseweb="tab"] {
        color: #70e7d1 !important;
        opacity: 0.7;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        padding: 8px 16px !important;
        border-radius: 6px !important;
        border: none !important;
        transition: all 0.2s;
    }
    .stTabs [data-baseweb="tab"]:hover {
        opacity: 1;
    }
    .stTabs [aria-selected="true"] {
        color: #06191d !important; /* Deep Dark Teal text */
        background-color: #00c5c8 !important; /* Electric Turquoise background */
        font-weight: 700 !important;
        box-shadow: 0 4px 12px rgba(0, 197, 200, 0.3);
        opacity: 1;
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
        background: linear-gradient(135deg, #00c5c8 0%, #70e7d1 100%) !important;
        color: #06191d !important; /* Readability: deep dark teal text */
        border: none !important;
        box-shadow: 0 4px 15px rgba(0, 197, 200, 0.25) !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #00b0b3 0%, #5ad8c1 100%) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 20px rgba(0, 197, 200, 0.4) !important;
    }

    .stDownloadButton > button {
        background-color: #0c383f !important;
        border: 1px solid #00c5c8 !important;
        color: #ccfbf1 !important;
        box-shadow: 0 4px 12px rgba(0, 197, 200, 0.15) !important;
    }
    .stDownloadButton > button:hover {
        background-color: #0e4e58 !important;
        color: white !important;
        border-color: #70e7d1 !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 18px rgba(0, 197, 200, 0.3) !important;
    }

    /* Expanders & details dropdowns */
    .streamlit-expanderHeader {
        background-color: #0e282c !important;
        border: 1px solid rgba(0, 197, 200, 0.15) !important;
        border-radius: 10px !important;
        font-size: 0.9rem !important;
        font-weight: 600 !important;
        color: #ffffff !important;
        margin-bottom: 0.4rem !important;
    }
    .streamlit-expanderContent {
        border-left: 1px solid rgba(0, 197, 200, 0.15) !important;
        border-right: 1px solid rgba(0, 197, 200, 0.15) !important;
        border-bottom: 1px solid rgba(0, 197, 200, 0.15) !important;
        background-color: #030c0e !important;
        padding: 1.25rem !important;
        border-radius: 0 0 10px 10px !important;
    }

    /* Logs view block */
    .log-box {
        font-family: 'JetBrains Mono', monospace !important;
        background-color: #03080a !important;
        border: 1px solid rgba(0, 197, 200, 0.2) !important;
        border-radius: 10px !important;
        padding: 1rem !important;
        height: 250px !important;
        overflow-y: auto !important;
        color: #70e7d1 !important;
        font-size: 0.85rem !important;
        line-height: 1.5 !important;
        box-shadow: inset 0 2px 6px rgba(0, 0, 0, 0.8) !important;
    }

    /* Alert notification boxes */
    div[data-testid="stNotification"] {
        background-color: #0e282c !important;
        border: 1px solid rgba(0, 197, 200, 0.2) !important;
        color: #e2e8f0 !important;
        border-radius: 10px !important;
    }

    /* Custom badges (pills) */
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

import streamlit as st

def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

    /* Font Family Settings */
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    /* Overall Sleek Charcoal Background */
    .stApp {
        background: radial-gradient(circle at 50% 50%, #181922 0%, #0d0e12 100%);
        color: #e2e8f0;
    }

    /* Premium Header Container */
    .header-container {
        padding: 2.2rem;
        background: linear-gradient(135deg, rgba(27, 29, 39, 0.6) 0%, rgba(13, 14, 18, 0.9) 100%);
        border: 1px solid rgba(6, 182, 212, 0.2);
        border-radius: 16px;
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.8), 0 0 15px rgba(6, 182, 212, 0.05);
        backdrop-filter: blur(12px);
        margin-bottom: 2.2rem;
        position: relative;
        overflow: hidden;
    }
    
    .header-container::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(6, 182, 212, 0.06) 0%, transparent 60%);
        pointer-events: none;
    }
    
    /* Crisp White Title with Soft Cyan Text Shadows */
    .main-title {
        font-size: 2.8rem;
        font-weight: 800;
        color: #ffffff !important;
        letter-spacing: -0.02em;
        margin-bottom: 0.5rem;
        text-shadow: 0 0 30px rgba(6, 182, 212, 0.2);
    }
    
    /* Muted Silver Subtitle */
    .sub-title {
        font-size: 1.05rem;
        font-weight: 400;
        color: #94a3b8;
        letter-spacing: 0.01em;
    }

    /* Sidebar - Deep Charcoal */
    section[data-testid="stSidebar"] {
        background: #090a0d;
        border-right: 1px solid rgba(6, 182, 212, 0.15);
    }
    
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stFileUploader label,
    section[data-testid="stSidebar"] .stRadio label,
    section[data-testid="stSidebar"] .stTextInput label,
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #06b6d4 !important; /* Electric Teal */
        font-size: 0.85rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        margin-bottom: 6px;
    }

    /* KPI Cards Container styling */
    .metric-card {
        background: rgba(24, 25, 34, 0.75);
        border: 1px solid rgba(255, 255, 255, 0.04);
        border-radius: 12px;
        padding: 1.4rem;
        box-shadow: 0 8px 20px -5px rgba(0, 0, 0, 0.6);
        backdrop-filter: blur(10px);
        transition: all 0.25s ease-in-out;
        position: relative;
        overflow: hidden;
    }
    
    .metric-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 15px 30px -8px rgba(0, 0, 0, 0.7);
        border-color: rgba(6, 182, 212, 0.3);
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
        border-left: 4px solid #06b6d4;
    }
    .metric-total .metric-value {
        color: #22d3ee; /* Light Teal */
    }

    .metric-passed {
        border-left: 4px solid #10b981;
    }
    .metric-passed .metric-value {
        color: #34d399; /* Mint Green */
    }

    .metric-warnings {
        border-left: 4px solid #f59e0b;
    }
    .metric-warnings .metric-value {
        color: #fbbf24; /* Amber */
    }

    .metric-failed {
        border-left: 4px solid #ef4444;
    }
    .metric-failed .metric-value {
        color: #f87171; /* Rose */
    }

    /* Tabs Component Styling */
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(13, 14, 18, 0.8);
        border-radius: 10px;
        padding: 5px;
        border: 1px solid rgba(6, 182, 212, 0.15);
        gap: 6px;
    }
    .stTabs [data-baseweb="tab"] {
        color: #94a3b8;
        font-weight: 600;
        font-size: 0.88rem;
        padding: 8px 16px;
        border-radius: 6px;
        border: none;
        transition: all 0.2s;
    }
    .stTabs [aria-selected="true"] {
        color: #ffffff !important;
        background: #0891b2 !important; /* Dark Teal */
        font-weight: 700;
        box-shadow: 0 4px 12px rgba(8, 145, 178, 0.3);
    }

    /* Custom buttons (primary & download) */
    .stButton > button {
        border-radius: 10px;
        font-weight: 700;
        font-size: 0.95rem;
        letter-spacing: 0.02em;
        transition: all 0.25s ease-in-out;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #0891b2 0%, #06b6d4 100%);
        color: white;
        border: none;
        box-shadow: 0 4px 15px rgba(6, 182, 212, 0.25);
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #0e7490 0%, #0891b2 100%);
        transform: translateY(-1px);
        box-shadow: 0 6px 20px rgba(6, 182, 212, 0.4);
    }

    .stDownloadButton > button {
        background: #0f766e;
        border: 1px solid #14b8a6;
        color: #ccfbf1;
        box-shadow: 0 4px 12px rgba(20, 184, 166, 0.15);
    }
    .stDownloadButton > button:hover {
        background: #0d9488;
        color: white;
        border-color: #2dd4bf;
        transform: translateY(-1px);
        box-shadow: 0 6px 18px rgba(20, 184, 166, 0.3);
    }

    /* Expanders & collapse details layout */
    .streamlit-expanderHeader {
        background-color: rgba(24, 25, 34, 0.6) !important;
        border: 1px solid rgba(6, 182, 212, 0.15) !important;
        border-radius: 10px !important;
        font-size: 0.9rem !important;
        font-weight: 600;
        color: #ffffff !important;
        margin-bottom: 0.4rem;
    }
    .streamlit-expanderContent {
        border-left: 1px solid rgba(6, 182, 212, 0.15) !important;
        border-right: 1px solid rgba(6, 182, 212, 0.15) !important;
        border-bottom: 1px solid rgba(6, 182, 212, 0.15) !important;
        background-color: rgba(13, 14, 18, 0.9);
        padding: 1.25rem !important;
        border-radius: 0 0 10px 10px;
    }

    /* Logs view block */
    .log-box {
        font-family: 'JetBrains Mono', monospace;
        background: #050608;
        border: 1px solid rgba(6, 182, 212, 0.2);
        border-radius: 10px;
        padding: 1rem;
        height: 250px;
        overflow-y: auto;
        color: #2dd4bf;
        font-size: 0.85rem;
        line-height: 1.5;
        box-shadow: inset 0 2px 6px rgba(0, 0, 0, 0.7);
    }

    /* Validation custom badges (pills) */
    .qc-error-badge {
        background: #7f1d1d;
        color: #fca5a5;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 0.72rem;
        font-weight: 700;
        display: inline-block;
    }
    .qc-warn-badge {
        background: #78350f;
        color: #fde047;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 0.72rem;
        font-weight: 700;
        display: inline-block;
    }
    .qc-pass-badge {
        background: #064e3b;
        color: #6ee7b7;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 0.72rem;
        font-weight: 700;
        display: inline-block;
    }

    </style>
    """, unsafe_allow_html=True)

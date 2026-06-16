import streamlit as st

def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

    /* Font override */
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }

    /* Overall App Layout */
    .stApp {
        background: radial-gradient(circle at 10% 20%, #1e1b4b 0%, #0f172a 45%, #020617 100%);
        color: #f1f5f9;
    }

    /* Premium Header Card */
    .header-container {
        padding: 2.5rem;
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.5) 0%, rgba(15, 23, 42, 0.8) 100%);
        border: 1px solid rgba(99, 102, 241, 0.2);
        border-radius: 20px;
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.7), 0 0 20px rgba(99, 102, 241, 0.1);
        backdrop-filter: blur(16px);
        margin-bottom: 2.5rem;
        text-align: left;
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
        background: radial-gradient(circle, rgba(129, 140, 248, 0.08) 0%, transparent 60%);
        pointer-events: none;
    }
    
    .main-title {
        font-size: 3rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        background: linear-gradient(90deg, #38bdf8 0%, #818cf8 35%, #c084fc 70%, #f472b6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.75rem;
        text-shadow: 0 0 40px rgba(129, 140, 248, 0.15);
    }
    
    .sub-title {
        font-size: 1.15rem;
        font-weight: 400;
        color: #cbd5e1;
        letter-spacing: 0.01em;
        opacity: 0.9;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background: #090d16;
        border-right: 1px solid rgba(99, 102, 241, 0.15);
    }
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stFileUploader label,
    section[data-testid="stSidebar"] .stRadio label,
    section[data-testid="stSidebar"] .stTextInput label,
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #818cf8 !important;
        font-size: 0.85rem;
        font-weight: 700;
        letter-spacing: 0.07em;
        text-transform: uppercase;
        margin-bottom: 6px;
    }

    /* Column Mapping Alignment styling cards */
    .stSelectbox div[data-baseweb="select"] {
        border-radius: 10px;
    }

    /* Colorful Glassmorphism KPI Card Styling */
    .metric-card {
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
        backdrop-filter: blur(12px);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    .metric-card:hover {
        transform: translateY(-4px) scale(1.02);
        box-shadow: 0 20px 35px -10px rgba(0, 0, 0, 0.6);
    }

    .metric-title {
        font-size: 0.85rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #94a3b8;
        margin-bottom: 0.5rem;
    }
    
    .metric-value {
        font-size: 2.25rem;
        font-weight: 800;
        font-family: 'JetBrains Mono', monospace;
        letter-spacing: -0.02em;
    }

    /* Card Themes */
    .metric-total {
        background: linear-gradient(135deg, rgba(14, 165, 233, 0.15) 0%, rgba(3, 105, 161, 0.05) 100%);
        border: 1px solid rgba(14, 165, 233, 0.3);
    }
    .metric-total .metric-value {
        color: #38bdf8;
        text-shadow: 0 0 15px rgba(14, 165, 233, 0.4);
    }
    .metric-total::after {
        content: '📊';
        position: absolute; right: 10px; bottom: 5px; font-size: 3rem; opacity: 0.07;
    }

    .metric-passed {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(4, 120, 87, 0.05) 100%);
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .metric-passed .metric-value {
        color: #34d399;
        text-shadow: 0 0 15px rgba(16, 185, 129, 0.4);
    }
    .metric-passed::after {
        content: '✨';
        position: absolute; right: 10px; bottom: 5px; font-size: 3rem; opacity: 0.07;
    }

    .metric-warnings {
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.15) 0%, rgba(180, 83, 9, 0.05) 100%);
        border: 1px solid rgba(245, 158, 11, 0.3);
    }
    .metric-warnings .metric-value {
        color: #fbbf24;
        text-shadow: 0 0 15px rgba(245, 158, 11, 0.4);
    }
    .metric-warnings::after {
        content: '⚠️';
        position: absolute; right: 10px; bottom: 5px; font-size: 3rem; opacity: 0.07;
    }

    .metric-failed {
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(185, 28, 28, 0.05) 100%);
        border: 1px solid rgba(239, 68, 68, 0.3);
    }
    .metric-failed .metric-value {
        color: #f87171;
        text-shadow: 0 0 15px rgba(239, 68, 68, 0.4);
    }
    .metric-failed::after {
        content: '❌';
        position: absolute; right: 10px; bottom: 5px; font-size: 3rem; opacity: 0.07;
    }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(15, 23, 42, 0.6);
        border-radius: 12px;
        padding: 6px;
        border: 1px solid rgba(99, 102, 241, 0.15);
        gap: 8px;
        box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.3);
    }
    .stTabs [data-baseweb="tab"] {
        color: #94a3b8;
        font-weight: 600;
        font-size: 0.9rem;
        padding: 10px 20px;
        border-radius: 8px;
        border: none;
        transition: all 0.2s;
    }
    .stTabs [aria-selected="true"] {
        color: #ffffff !important;
        background: linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%) !important;
        font-weight: 700;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
    }

    /* Action Buttons */
    .stButton > button {
        border-radius: 12px;
        font-weight: 700;
        font-size: 1rem;
        padding: 0.6rem 2rem;
        letter-spacing: 0.03em;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    /* Primary Action Buttons */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #0ea5e9 0%, #a855f7 50%, #ec4899 100%);
        color: white;
        border: none;
        box-shadow: 0 4px 20px rgba(168, 85, 247, 0.35);
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #38bdf8 0%, #c084fc 50%, #f472b6 100%);
        transform: translateY(-2px);
        box-shadow: 0 8px 30px rgba(168, 85, 247, 0.6);
    }

    /* Download Buttons */
    .stDownloadButton > button {
        background: linear-gradient(135deg, #059669 0%, #10b981 100%);
        border: none;
        color: #ffffff;
        box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);
        border-radius: 12px;
        font-weight: 700;
    }
    .stDownloadButton > button:hover {
        background: linear-gradient(135deg, #047857 0%, #059669 100%);
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(16, 185, 129, 0.55);
        color: white;
    }

    /* Expander / Details Card Headers */
    .streamlit-expanderHeader {
        background-color: rgba(30, 41, 59, 0.5) !important;
        border: 1px solid rgba(99, 102, 241, 0.15) !important;
        border-radius: 12px !important;
        font-size: 0.95rem !important;
        font-weight: 600;
        color: #f1f5f9 !important;
        margin-bottom: 0.5rem;
    }
    .streamlit-expanderContent {
        border-left: 1px solid rgba(99, 102, 241, 0.15) !important;
        border-right: 1px solid rgba(99, 102, 241, 0.15) !important;
        border-bottom: 1px solid rgba(99, 102, 241, 0.15) !important;
        background-color: rgba(15, 23, 42, 0.85);
        padding: 1.5rem !important;
        border-radius: 0 0 12px 12px;
    }

    /* Log Output Box */
    .log-box {
        font-family: 'JetBrains Mono', monospace;
        background: #030712;
        border: 1px solid rgba(99, 102, 241, 0.2);
        border-radius: 12px;
        padding: 1.25rem;
        height: 300px;
        overflow-y: auto;
        color: #34d399;
        font-size: 0.88rem;
        line-height: 1.6;
        box-shadow: inset 0 2px 8px rgba(0, 0, 0, 0.8);
    }

    /* Styled Badges */
    .qc-error-badge {
        background: linear-gradient(135deg, #ef4444 0%, #b91c1c 100%);
        color: #ffffff;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.03em;
        display: inline-block;
        box-shadow: 0 2px 8px rgba(239, 68, 68, 0.35);
    }
    .qc-warn-badge {
        background: linear-gradient(135deg, #f59e0b 0%, #b45309 100%);
        color: #ffffff;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.03em;
        display: inline-block;
        box-shadow: 0 2px 8px rgba(245, 158, 11, 0.35);
    }
    .qc-pass-badge {
        background: linear-gradient(135deg, #10b981 0%, #047857 100%);
        color: #ffffff;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.03em;
        display: inline-block;
        box-shadow: 0 2px 8px rgba(16, 185, 129, 0.35);
    }

    </style>
    """, unsafe_allow_html=True)

import io
import os
import pandas as pd
import streamlit as st
from datetime import datetime

# Set page config at the very beginning
st.set_page_config(
    page_title="Listing QC Validation Tool",
    page_icon="✅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import local modules
from utils.styles import inject_css
from utils.file_loaders import (
    load_file_to_df, 
    load_google_sheet, 
    auto_map_columns, 
    standardize_dataframe,
    CANONICAL_LABELS,
    load_content,
    load_zecom,
    _safe_str
)
from utils.validators import (
    validate_dataframe, 
    compare_source_and_live,
    ALLOWED_GENDERS,
    ALLOWED_STATUSES
)
from utils.report_generator import (
    generate_qc_excel_report,
    generate_comparison_excel_report
)

# Inject custom CSS
inject_css()

# App Header
st.markdown("""
<div class="header-container">
    <div class="main-title">Listing QC Validation Tool</div>
    <div class="sub-title">Automated internal quality control validation and post-listing store sync analysis.</div>
</div>
""", unsafe_allow_html=True)

# List of 10 channels
CHANNELS = [
    "Lazada SG", "Lazada MY", "Lazada PH",
    "Shopee SG", "Shopee MY", "Shopee PH",
    "Zalora SG", "Zalora MY", "Zalora PH",
    "TikTok MY"
]

# Initialize Session States
if "ran_validation" not in st.session_state:
    st.session_state.ran_validation = False
if "val_df" not in st.session_state:
    st.session_state.val_df = pd.DataFrame()
if "exc_df" not in st.session_state:
    st.session_state.exc_df = pd.DataFrame()
if "logs" not in st.session_state:
    st.session_state.logs = []
if "qc_stage" not in st.session_state:
    st.session_state.qc_stage = "Internal QC"
if "channel" not in st.session_state:
    st.session_state.channel = "Lazada PH"

if "ran_comparison" not in st.session_state:
    st.session_state.ran_comparison = False
if "comp_df" not in st.session_state:
    st.session_state.comp_df = pd.DataFrame()
if "comp_metrics" not in st.session_state:
    st.session_state.comp_metrics = {}

# ── Sidebar Configurations ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Channel & Stage Settings")
    channel = st.selectbox(
        "Target Marketplace Channel",
        options=CHANNELS,
        index=CHANNELS.index("Shopee PH") if "Shopee PH" in CHANNELS else 5
    )
    st.session_state.channel = channel
    
    channel_parts = channel.split()
    platform = channel_parts[0]
    country = channel_parts[1]

    qc_stage = st.selectbox(
        "QC Process Stage",
        ["Internal QC", "Post QC"],
        help="Internal QC validates pre-listing fields. Post QC includes image links, size charts, and live list audits."
    )
    st.session_state.qc_stage = qc_stage

    st.markdown("---")
    st.markdown("### Upload Reference Files")
    
    # 1. Content File (Mandatory)
    content_file = st.file_uploader(
        "Upload Content File (EAN, UK Size reference)",
        type=["xlsx", "xls", "csv"],
        key="ref_content"
    )
    
    # 2. zEcom File (Mandatory)
    zecom_file = st.file_uploader(
        "Upload zEcom File (Ecom Status, RRP Price reference)",
        type=["xlsx", "xls", "csv"],
        key="ref_zecom"
    )
    
    # 3. Post QC Channel Marketplace Files
    live_file_gen = None
    live_file_media = None
    
    if qc_stage == "Post QC":
        st.markdown("---")
        st.markdown("### Upload Live Marketplace Files")
        live_file_gen = st.file_uploader(
            "1. Upload Live Listings (General QC Check: Status, Price, Stock)",
            type=["xlsx", "xls", "csv", "zip"],
            key="live_gen"
        )
        live_file_media = st.file_uploader(
            "2. Upload Live Listings (Media Check: Images & Size Chart)",
            type=["xlsx", "xls", "csv", "zip"],
            key="live_media"
        )

    st.markdown("---")
    st.markdown("### Upload Target Listings Sheet")
    input_mode = st.radio(
        "Upload Sheet Mode",
        ["File Upload (Excel/CSV)", "Google Sheets Link"]
    )
    
    upload_dfs = {}
    if input_mode == "File Upload (Excel/CSV)":
        if "gsheet_error" in st.session_state:
            del st.session_state["gsheet_error"]
        uploaded_files = st.file_uploader(
            "Upload Target Sheet",
            type=["xlsx", "xls", "csv"],
            accept_multiple_files=True,
            key="target_uploader"
        )
        if uploaded_files:
            for f in uploaded_files:
                try:
                    df = load_file_to_df(f)
                    upload_dfs[f.name] = df
                except Exception as e:
                    st.error(f"Error loading target file {f.name}: {e}")
    else:
        gsheet_url = st.text_input(
            "Google Sheets Share Link",
            placeholder="https://docs.google.com/spreadsheets/d/..."
        )
        if not gsheet_url:
            if "gsheet_error" in st.session_state:
                del st.session_state["gsheet_error"]
        else:
            try:
                with st.spinner("Downloading Google Sheet..."):
                    df = load_google_sheet(gsheet_url)
                    upload_dfs["Google Sheet"] = df
                    if "gsheet_error" in st.session_state:
                        del st.session_state["gsheet_error"]
            except Exception as e:
                err_str = str(e)
                st.session_state["gsheet_error"] = err_str
                if "401" in err_str or "unauthorized" in err_str.lower() or "forbidden" in err_str.lower() or "403" in err_str:
                    st.error("""
                    🔒 **Private Google Sheet detected (HTTP 401/403):**
                    
                    The app does not have permission to fetch this private sheet.
                    
                    **To resolve this:**
                    1. In your Google Sheet, click the blue **Share** button in the top right.
                    2. Under *General Access*, change it from *Restricted* to **"Anyone with the link can view"** (Viewer access).
                    3. Copy the new link and paste it here.
                    
                    *Alternatively:* Go to Google Sheets ➔ **File** ➔ **Download** ➔ **Microsoft Excel (.xlsx)** or **Comma Separated Values (.csv)**, and upload it using the **FILE UPLOAD** mode above.
                    """)
                else:
                    st.error(f"Failed to fetch sheet: {e}. Check if sharing settings are set to public 'Anyone with the link'.")

    with st.expander("Genders & Statuses Config"):
        custom_genders_str = st.text_input(
            "Allowed Genders",
            value=", ".join(ALLOWED_GENDERS)
        )
        custom_genders = [g.strip().lower() for g in custom_genders_str.split(",") if g.strip()]
        
        custom_statuses_str = st.text_input(
            "Allowed Ecom Statuses",
            value=", ".join(ALLOWED_STATUSES)
        )
        custom_statuses = [s.strip().lower() for s in custom_statuses_str.split(",") if s.strip()]
        
        check_live_images = st.checkbox("Live HTTP Image Check", value=False)

# ── Main Content Area ────────────────────────────────────────────────────────
# ── Setup Checklist Dashboard ────────────────────────────────────────────────
content_loaded = content_file is not None
zecom_loaded = zecom_file is not None
target_loaded = len(upload_dfs) > 0
gsheet_error = st.session_state.get("gsheet_error")

# Determine if we should show the setup checklist dashboard
show_setup_dashboard = not (content_loaded and zecom_loaded and target_loaded)

if show_setup_dashboard:
    st.markdown("---")
    st.subheader("🛠️ QC Validation Setup Dashboard")
    st.markdown("Please configure the required files and parameters in the sidebar to begin. Below is the current configuration status:")

    # Create columns for the checklist cards
    card_cols = st.columns(3)

    # Card 1: Target Listings Sheet
    with card_cols[0]:
        st.markdown("""
        <div class="metric-card" style="border-top: 4px solid #d946ef; height: 100%;">
            <div class="metric-title">1. Target Listings Sheet</div>
        """, unsafe_allow_html=True)
        
        if target_loaded:
            fn_list = list(upload_dfs.keys())
            fn_str = ", ".join(fn_list)
            st.markdown(f"**Status**: ✅ Loaded<br><span style='font-size:0.85rem; color:#a7f3d0;'>{fn_str}</span>", unsafe_allow_html=True)
        elif gsheet_error:
            st.markdown("**Status**: ❌ Error<br><span style='font-size:0.85rem; color:#fca5a5;'>Failed to download Google Sheet</span>", unsafe_allow_html=True)
        else:
            st.markdown("**Status**: ❌ Missing<br><span style='font-size:0.85rem; color:#cbd5e1;'>Upload Target Sheet in sidebar</span>", unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)

    # Card 2: Required Reference Files
    with card_cols[1]:
        st.markdown("""
        <div class="metric-card" style="border-top: 4px solid #3b82f6; height: 100%;">
            <div class="metric-title">2. Required References</div>
        """, unsafe_allow_html=True)
        
        # Content File status
        if content_loaded:
            st.markdown(f"**Content File**: ✅ Loaded<br><span style='font-size:0.8rem; color:#a7f3d0;'>{content_file.name}</span>", unsafe_allow_html=True)
        else:
            st.markdown("**Content File**: ❌ Missing", unsafe_allow_html=True)
            
        st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)
        
        # zEcom File status
        if zecom_loaded:
            st.markdown(f"**zEcom File**: ✅ Loaded<br><span style='font-size:0.8rem; color:#a7f3d0;'>{zecom_file.name}</span>", unsafe_allow_html=True)
        else:
            st.markdown("**zEcom File**: ❌ Missing", unsafe_allow_html=True)
            
        st.markdown("</div>", unsafe_allow_html=True)

    # Card 3: Marketplace Parameters
    with card_cols[2]:
        st.markdown(f"""
        <div class="metric-card" style="border-top: 4px solid #10b981; height: 100%;">
            <div class="metric-title">3. Channel & Settings</div>
            <div><b>Channel</b>: <span style="color:#6ee7b7;">{channel}</span></div>
            <div style="margin-top: 6px;"><b>Stage</b>: <span style="color:#6ee7b7;">{qc_stage}</span></div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Detailed Google Sheet error callout in main area if present
    if gsheet_error:
        if "401" in gsheet_error or "unauthorized" in gsheet_error.lower() or "forbidden" in gsheet_error.lower() or "403" in gsheet_error:
            st.error(f"""
            🔒 **Private Google Sheet detected (HTTP 401/403):**
            
            The app does not have permission to fetch this private sheet.
            
            **How to resolve this:**
            1. In your Google Sheet, click the blue **Share** button in the top right.
            2. Under *General Access*, change it from *Restricted* to **"Anyone with the link can view"** (Viewer access).
            3. Copy the new link and paste it in the sidebar.
            
            *Alternatively:* Go to Google Sheets ➔ **File** ➔ **Download** ➔ **Microsoft Excel (.xlsx)** or **Comma Separated Values (.csv)**, and upload it using the **FILE UPLOAD** mode in the sidebar.
            
            **Raw Error:** `{gsheet_error}`
            """)
        else:
            st.error(f"❌ **Error downloading Google Sheet:** {gsheet_error}\n\nPlease verify that the URL is correct and public 'Anyone with the link can view'.")

    # Show a helpful guide in the main area when files are missing
    if not target_loaded and not gsheet_error:
        st.info("💡 **Getting Started:** Use the sidebar control panel to upload your listing files. You will need a target listings file and reference content/zEcom files.")
        
    if target_loaded and not (content_loaded and zecom_loaded):
        st.warning("⚠️ **Reference Files Needed:** You have uploaded the target sheet, but you must upload both the **Content File** and **zEcom File** in the sidebar to run validations. Since they are at the top of the sidebar, you may need to **scroll up** in the sidebar to find their file uploaders.")

# ── Main Content Area ────────────────────────────────────────────────────────
if target_loaded:
    # ── Column Mapping Step ───────────────────────────────────────────────────
    st.subheader("📋 Column Mapping Alignment (Upload Sheet)")
    st.markdown("Align the columns in your uploaded target sheet to the standard QC validation fields:")
    
    # Collect all headers across uploaded files
    all_headers = []
    for fn, df in upload_dfs.items():
        all_headers.extend(df.columns.tolist())
    all_headers = sorted(list(set(all_headers)))
    
    # Run auto-mapper
    auto_maps = auto_map_columns(all_headers)
    
    # Define mapping columns (exclude Post QC fields if Internal QC is selected)
    fields_to_map = list(CANONICAL_LABELS.keys())
    if qc_stage == "Internal QC":
        fields_to_map = [f for f in fields_to_map if f not in ["images", "size_chart"]]
        
    cols = st.columns(3)
    manual_mapping = {}
    
    for i, canonical in enumerate(fields_to_map):
        col_selector = cols[i % 3]
        default_val = auto_maps.get(canonical)
        
        options = ["-- Skip / Missing --"] + all_headers
        default_idx = 0
        if default_val in all_headers:
            default_idx = options.index(default_val)
            
        with col_selector:
            mapped_col = st.selectbox(
                f"{CANONICAL_LABELS[canonical]}",
                options=options,
                index=default_idx,
                key=f"map_{canonical}"
            )
            manual_mapping[canonical] = None if mapped_col == "-- Skip / Missing --" else mapped_col
            
    # Process & Validate Button
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Enable button only if reference files are loaded
    refs_missing = not (content_loaded and zecom_loaded)
    
    if refs_missing:
        st.warning("⚠️ Upload **Content File** and **zEcom File** in the sidebar to unlock the validation button.")
        st.button("🚀 Run QC Validation", type="primary", use_container_width=True, disabled=True, help="Reference files are required")
    else:
        if st.button("🚀 Run QC Validation", type="primary", use_container_width=True):
            with st.spinner("Loading references and running validations..."):
                try:
                    content_df = load_content(content_file)
                    zecom_df = load_zecom(zecom_file, country)
                    
                    all_standardized = []
                    for fn, df in upload_dfs.items():
                        std_df = standardize_dataframe(df, manual_mapping, source_name=fn)
                        all_standardized.append(std_df)
                    combined_df = pd.concat(all_standardized, ignore_index=True)
                    
                    # Execute validation rules
                    exc_df, val_df, logs = validate_dataframe(
                        combined_df, 
                        qc_stage=qc_stage,
                        channel=channel,
                        content_df=content_df,
                        zecom_df=zecom_df,
                        check_live_images=check_live_images,
                        allowed_genders=custom_genders,
                        allowed_statuses=custom_statuses
                    )
                    
                    st.session_state.val_df = val_df
                    st.session_state.exc_df = exc_df
                    st.session_state.logs = logs
                    st.session_state.ran_validation = True
                    
                    st.session_state.ran_comparison = False
                    
                except Exception as e:
                    st.error(f"Error executing validation run: {e}")
                    import traceback
                    st.error(traceback.format_exc())

    # ── Validation Results View ───────────────────────────────────────────────
    if st.session_state.ran_validation:
        st.markdown("---")
        st.subheader("📊 Validation Results Dashboard")
        
        val_df = st.session_state.val_df
        exc_df = st.session_state.exc_df
        logs = st.session_state.logs
        
        total_records = len(val_df)
        total_skus = val_df["sku"].nunique() if "sku" in val_df.columns else 0
        total_articles = val_df["article_number"].nunique() if "article_number" in val_df.columns else 0
        total_exceptions = len(exc_df) if not exc_df.empty else 0
        
        kpi_cols = st.columns(3)
        with kpi_cols[0]:
            st.markdown(f'<div class="metric-card metric-total"><div class="metric-title">Total Rows Audited</div><div class="metric-value">{total_records}</div></div>', unsafe_allow_html=True)
        with kpi_cols[1]:
            st.markdown(f'<div class="metric-card metric-passed" style="border-left-color: #38bdf8 !important;"><div class="metric-title" style="color: #38bdf8 !important;">Total Unique SKUs</div><div class="metric-value" style="color: #38bdf8 !important;">{total_skus}</div></div>', unsafe_allow_html=True)
        with kpi_cols[2]:
            st.markdown(f'<div class="metric-card metric-warnings" style="border-left-color: #a78bfa !important;"><div class="metric-title" style="color: #a78bfa !important;">Total Unique Articles</div><div class="metric-value" style="color: #a78bfa !important;">{total_articles}</div></div>', unsafe_allow_html=True)
            
        # Create containers/tabs depending on QC stage
        if qc_stage == "Post QC":
            tab_list = st.tabs(["📊 Dashboard & Data View", "🔄 Live Listing Sync Audit"])
            container_dashboard = tab_list[0]
            container_live = tab_list[1]
        else:
            container_dashboard = st.container()
            container_live = None

        with container_dashboard:
            # Build Checklist Metrics
            # 1. zEcom Status check (only for 13-digit child SKUs)
            child_df = val_df[val_df["sku"].dropna().astype(str).str.strip().str.match(r'^\d{13}$')]
            no_status_count = sum(child_df["Zeocm Status"] != "Yes")
            status_ok = no_status_count == 0
            status_badge = '<span class="qc-status-ok">OK</span>' if status_ok else '<span class="qc-status-mismatch">Mismatch</span>'
            status_text = "Yes for all articles" if status_ok else f"{no_status_count} records are 'No' or 'Not Found'"
            
            # 2. Launch Date check
            launch_excs = exc_df[exc_df["Field"] == "Launch Date"] if not exc_df.empty else pd.DataFrame()
            launch_ok = launch_excs.empty
            launch_badge = '<span class="qc-status-ok">OK</span>' if launch_ok else '<span class="qc-status-mismatch">Mismatch</span>'
            launch_rows = launch_excs.groupby(["Source File", "Row Number"]).ngroups if not launch_ok else 0
            launch_text = "All launch dates are past/current" if launch_ok else f"{launch_rows} future launch dates flagged"
            
            # 3. Gender check
            gender_excs = exc_df[exc_df["Field"] == "Gender"] if not exc_df.empty else pd.DataFrame()
            gender_ok = gender_excs.empty
            gender_badge = '<span class="qc-status-ok">OK</span>' if gender_ok else '<span class="qc-status-mismatch">Mismatch</span>'
            gender_rows = gender_excs.groupby(["Source File", "Row Number"]).ngroups if not gender_ok else 0
            gender_text = "All genders compatible" if gender_ok else f"{gender_rows} gender mismatches found"
            
            # 4. Color Name check
            color_excs = exc_df[exc_df["Field"] == "Color Name"] if not exc_df.empty else pd.DataFrame()
            color_ok = color_excs.empty
            color_badge = '<span class="qc-status-ok">OK</span>' if color_ok else '<span class="qc-status-mismatch">Mismatch</span>'
            color_rows = color_excs.groupby(["Source File", "Row Number"]).ngroups if not color_ok else 0
            color_text = "All color names match Content file" if color_ok else f"{color_rows} color mismatches found"
            
            # 5. Size check
            size_excs = exc_df[exc_df["Field"] == "Size"] if not exc_df.empty else pd.DataFrame()
            size_ok = size_excs.empty
            size_badge = '<span class="qc-status-ok">OK</span>' if size_ok else '<span class="qc-status-mismatch">Mismatch</span>'
            size_rows = size_excs.groupby(["Source File", "Row Number"]).ngroups if not size_ok else 0
            size_text = "All sizes match Content file references" if size_ok else f"{size_rows} size mismatches found"
            
            # 6. Price Check
            price_excs = exc_df[exc_df["Field"] == "Price"] if not exc_df.empty else pd.DataFrame()
            price_ok = price_excs.empty
            price_badge = '<span class="qc-status-ok">OK</span>' if price_ok else '<span class="qc-status-mismatch">Mismatch</span>'
            price_rows = price_excs.groupby(["Source File", "Row Number"]).ngroups if not price_ok else 0
            price_text = "All prices match zEcom RRP" if price_ok else f"{price_rows} price mismatches found"
            
            # 7. Quantity check
            qty_excs = exc_df[exc_df["Field"] == "Quantity"] if not exc_df.empty else pd.DataFrame()
            qty_ok = qty_excs.empty
            qty_badge = '<span class="qc-status-ok">OK</span>' if qty_ok else '<span class="qc-status-mismatch">Mismatch</span>'
            qty_rows = qty_excs.groupby(["Source File", "Row Number"]).ngroups if not qty_ok else 0
            qty_text = "Quantity is 0 for all items" if qty_ok else f"{qty_rows} non-zero quantity items found"
            
            # Build QC Table HTML
            qc_table_html = f"""
            <table class="qc-table">
                <thead>
                    <tr>
                        <th>Check Name</th>
                        <th>Target Condition</th>
                        <th>Actual Status</th>
                        <th style="text-align: center; width: 120px;">Result</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td style="font-weight: 600;">zEcom Status Check</td>
                        <td>Should be 'Yes' for all articles</td>
                        <td>{status_text}</td>
                        <td style="text-align: center;">{status_badge}</td>
                    </tr>
                    <tr>
                        <td style="font-weight: 600;">Launch Date Check</td>
                        <td>Should not be in the future</td>
                        <td>{launch_text}</td>
                        <td style="text-align: center;">{launch_badge}</td>
                    </tr>
                    <tr>
                        <td style="font-weight: 600;">Gender Mismatch Check</td>
                        <td>Matches Content file gender reference</td>
                        <td>{gender_text}</td>
                        <td style="text-align: center;">{gender_badge}</td>
                    </tr>
                    <tr>
                        <td style="font-weight: 600;">Color Name Check</td>
                        <td>Matches Content file Color Name reference</td>
                        <td>{color_text}</td>
                        <td style="text-align: center;">{color_badge}</td>
                    </tr>
                    <tr>
                        <td style="font-weight: 600;">Size Check</td>
                        <td>Matches Content size (UK/US/Rus) reference</td>
                        <td>{size_text}</td>
                        <td style="text-align: center;">{size_badge}</td>
                    </tr>
                    <tr>
                        <td style="font-weight: 600;">Price Check</td>
                        <td>Matches zEcom RRP reference price</td>
                        <td>{price_text}</td>
                        <td style="text-align: center;">{price_badge}</td>
                    </tr>
                    <tr>
                        <td style="font-weight: 600;">Quantity Check</td>
                        <td>Quantity must be exactly 0 for all items</td>
                        <td>{qty_text}</td>
                        <td style="text-align: center;">{qty_badge}</td>
                    </tr>
                </tbody>
            </table>
            """
            
            st.markdown("### 📋 QC Quality Checklist")
            st.markdown(qc_table_html, unsafe_allow_html=True)
            
            st.markdown("### 🔍 Validated Dataset Preview")
            preview_df = val_df.copy()
            target_headers = {
                "sku": "Seller SKU",
                "article_number": "Article No",
                "Zeocm Status": "Zeocm Status",
                "launch_date": "Launch Date",
                "gender": "Gender",
                "product_name": "Product Name",
                "Gender Check": "Gender Check",
                "color_name": "Color Name",
                "ref_color_name": "Reference Color Name",
                "Color Check": "Color Check",
                "size": "Size",
                "ref_size": "Reference Size",
                "Size Check": "Size Check",
                "price": "RRP",
                "ref_rrp": "Reference RRP",
                "RRP Check": "RRP Check",
                "quantity": "Quantity"
            }
            for col in target_headers.keys():
                if col not in preview_df.columns:
                    preview_df[col] = ""
            ordered_cols = list(target_headers.keys())
            preview_df = preview_df[ordered_cols]
            preview_df = preview_df.rename(columns=target_headers)
            st.dataframe(preview_df.head(500), use_container_width=True, hide_index=True)
            
            st.markdown("#### 📥 Download Validation Reports")
            excel_data = generate_qc_excel_report(val_df, exc_df, qc_stage)
            
            st.download_button(
                label="📥 Download Detailed Excel QC Report",
                data=excel_data,
                file_name=f"Listing_QC_Report_{qc_stage}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

        if container_live is not None:
            with container_live:
                st.markdown("#### 🔄 Live Store Listing Sync Audit")
                st.markdown(f"Compare your uploaded listing sheet against live store data.")
                
                if not live_file_gen and not live_file_media:
                    st.info("💡 Please upload at least one Live listings file (General or Media Check) in the sidebar to run the sync audit.")
                else:
                    live_general_df = pd.DataFrame()
                    live_media_df = pd.DataFrame()
                    
                    if live_file_gen:
                        try:
                            live_general_df_raw = load_file_to_df(live_file_gen)
                            st.success(f"✅ Loaded General Live file ({len(live_general_df_raw)} records)")
                            
                            live_gen_cols = live_general_df_raw.columns.tolist()
                            live_gen_maps = auto_map_columns(live_gen_cols)
                            
                            with st.expander("Align Live General File Columns"):
                                l_cols = st.columns(3)
                                live_gen_mapping = {}
                                
                                gen_fields = ["sku", "ecommerce_status", "price", "quantity", "product_name"]
                                for i, canonical in enumerate(gen_fields):
                                    l_col_sel = l_cols[i % 3]
                                    l_default_val = live_gen_maps.get(canonical)
                                    l_options = ["-- Skip --"] + live_gen_cols
                                    l_default_idx = 0
                                    if l_default_val in live_gen_cols:
                                        l_default_idx = l_options.index(l_default_val)
                                    with l_col_sel:
                                        l_mapped_col = st.selectbox(
                                            f"Live {CANONICAL_LABELS[canonical]}",
                                            options=l_options,
                                            index=l_default_idx,
                                            key=f"live_gen_map_{canonical}"
                                        )
                                        live_gen_mapping[canonical] = None if l_mapped_col == "-- Skip --" else l_mapped_col
                                        
                            live_general_df = standardize_dataframe(live_general_df_raw, live_gen_mapping, source_name="Live General")
                        except Exception as e:
                            st.error(f"Failed to load Live General file: {e}")
                            
                    if live_file_media:
                        try:
                            live_media_df_raw = load_file_to_df(live_file_media)
                            st.success(f"✅ Loaded Images & Size Chart Live file ({len(live_media_df_raw)} records)")
                            
                            live_med_cols = live_media_df_raw.columns.tolist()
                            live_med_maps = auto_map_columns(live_med_cols)
                            
                            with st.expander("Align Live Media File Columns"):
                                l_cols = st.columns(3)
                                live_med_mapping = {}
                                
                                med_fields = ["sku", "images", "size_chart"]
                                for i, canonical in enumerate(med_fields):
                                    l_col_sel = l_cols[i % 3]
                                    l_default_val = live_med_maps.get(canonical)
                                    l_options = ["-- Skip --"] + live_med_cols
                                    l_default_idx = 0
                                    if l_default_val in live_med_cols:
                                        l_default_idx = l_options.index(l_default_val)
                                    with l_col_sel:
                                        l_mapped_col = st.selectbox(
                                            f"Live {CANONICAL_LABELS[canonical]}",
                                            options=l_options,
                                            index=l_default_idx,
                                            key=f"live_med_map_{canonical}"
                                        )
                                        live_med_mapping[canonical] = None if l_mapped_col == "-- Skip --" else l_mapped_col
                                        
                            live_media_df = standardize_dataframe(live_media_df_raw, live_med_mapping, source_name="Live Media")
                        except Exception as e:
                            st.error(f"Failed to load Live Media file: {e}")
                            
                    if st.button("🔄 Execute Comparison Audit", type="primary", key="btn_run_compare"):
                        with st.spinner("Consolidating live sheets and running comparison..."):
                            try:
                                if not live_general_df.empty and not live_media_df.empty:
                                    media_clean = live_media_df.drop(columns=["_original_row_number", "_source_file"])
                                    live_general_df["sku"] = live_general_df["sku"].astype(str).str.strip()
                                    media_clean["sku"] = media_clean["sku"].astype(str).str.strip()
                                    
                                    consolidated_live = pd.merge(
                                        live_general_df, 
                                        media_clean, 
                                        on="sku", 
                                        how="outer"
                                    )
                                elif not live_general_df.empty:
                                    consolidated_live = live_general_df
                                else:
                                    consolidated_live = live_media_df
                                    
                                standardized_source = val_df.copy()
                                
                                comp_df, comp_metrics = compare_source_and_live(
                                    standardized_source,
                                    consolidated_live,
                                    match_column="sku"
                                )
                                
                                st.session_state.comp_df = comp_df
                                st.session_state.comp_metrics = comp_metrics
                                st.session_state.ran_comparison = True
                            except Exception as e:
                                st.error(f"Comparison run failed: {e}")
                                import traceback
                                st.error(traceback.format_exc())
                            
                    if st.session_state.ran_comparison:
                        st.markdown("---")
                        st.markdown("##### Comparison Summary")
                        
                        comp_df = st.session_state.comp_df
                        comp_metrics = st.session_state.comp_metrics
                        
                        c_kpis = st.columns(5)
                        labels = list(comp_metrics.keys())
                        vals = list(comp_metrics.values())
                        theme_colors = ["#00c5c8", "#34d399", "#f87171", "#fbbf24", "#a78bfa"]
                        
                        for idx in range(len(labels)):
                            with c_kpis[idx]:
                                st.markdown(f'<div class="metric-card" style="border-top: 4px solid {theme_colors[idx]};"><div class="metric-title">{labels[idx]}</div><div class="metric-value" style="color: {theme_colors[idx]};">{vals[idx]}</div></div>', unsafe_allow_html=True)
                        
                        st.markdown("##### Detailed Discrepancy Table")
                        mismatches_only = comp_df[comp_df["Match Status"] != "Passed"]
                        
                        if mismatches_only.empty:
                            st.success("🎉 Perfect Sync! All compared attributes match perfectly between uploaded sheet and live store.")
                        else:
                            st.markdown(f"Found **{len(mismatches_only)}** discrepancies between sheets:")
                            st.dataframe(mismatches_only, use_container_width=True, hide_index=True)
                        
                        comp_excel_data = generate_comparison_excel_report(comp_df, comp_metrics)
                        st.download_button(
                            label="📥 Download Live Listing Comparison Excel Report",
                            data=comp_excel_data,
                            file_name=f"Live_Listing_Sync_Audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )

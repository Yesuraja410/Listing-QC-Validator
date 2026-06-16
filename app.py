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
    load_lazada,
    load_shopee_stock,
    load_shopee_status,
    load_zalora_stock,
    load_zalora_status,
    load_tiktok,
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
    
    # Extract country (SG, MY, PH) and platform (Lazada, Shopee, Zalora, TikTok)
    channel_parts = channel.split()
    platform = channel_parts[0]
    country = channel_parts[1]

    qc_stage = st.selectbox(
        "QC Process Stage",
        ["Internal QC", "Post QC"],
        help="Internal QC validates pre-listing fields. Post QC includes image links and size charts."
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
        "Upload zEcom File (Ecom Status, Launch Date reference)",
        type=["xlsx", "xls", "csv"],
        key="ref_zecom"
    )
    
    # 3. Post QC Channel Marketplace Files
    live_df = pd.DataFrame()
    live_loaded = False
    
    if qc_stage == "Post QC":
        st.markdown("---")
        st.markdown(f"### Upload Marketplace Files ({channel})")
        
        if platform == "Lazada":
            laz_file = st.file_uploader("Lazada Live listings report", type=["xlsx", "xls", "csv"], key="live_laz")
            if laz_file:
                live_df = load_lazada(laz_file, country)
                live_loaded = not live_df.empty
                
        elif platform == "Shopee":
            sh_stock_file = st.file_uploader("Shopee Stock report (ZIP/Excel)", type=["xlsx", "xls", "csv", "zip"], key="live_sh_stk")
            sh_status_file = st.file_uploader("Shopee Status/Basic Info report", type=["xlsx", "xls", "csv", "zip"], key="live_sh_sts")
            if sh_stock_file:
                sh_stock = load_shopee_stock(sh_stock_file, country)
                sh_status = load_shopee_status(sh_status_file, country)
                
                if not sh_stock.empty:
                    shopee = sh_stock.copy()
                    active_pids = set()
                    if not sh_status.empty and "Product ID" in sh_status.columns:
                        active_pids = set(
                            sh_status["Product ID"]
                            .apply(_safe_str)
                            .str.strip()
                            .replace("", pd.NA)
                            .dropna()
                            .unique()
                        )
                    
                    if "Product ID" in shopee.columns:
                        if active_pids and len(active_pids & set(shopee["Product ID"].apply(_safe_str).str.strip())) > 0:
                            shopee["MP Status"] = shopee["Product ID"].apply(
                                lambda x: "Active" if _safe_str(x).strip() in active_pids else "Inactive"
                            )
                        else:
                            shopee["MP Status"] = shopee["Product ID"].apply(
                                lambda x: "Active" if _safe_str(x).strip() not in ("", "nan", "none") else "Inactive"
                            )
                    else:
                        shopee["MP Status"] = "Inactive"
                    live_df = shopee
                    live_loaded = True
                    
        elif platform == "Zalora":
            z_stock_file = st.file_uploader("Zalora Stock file", type=["xlsx", "xls", "csv"], key="live_z_stk")
            z_status_file = st.file_uploader("Zalora Status file", type=["xlsx", "xls", "csv"], key="live_z_sts")
            if z_stock_file:
                z_stock = load_zalora_stock(z_stock_file, country)
                z_status = load_zalora_status(z_status_file, country)
                if not z_stock.empty and not z_status.empty and "SKU" in z_stock.columns and "SKU" in z_status.columns:
                    live_df = pd.merge(z_stock, z_status[["SKU", "MP Status"]], on="SKU", how="left")
                else:
                    live_df = z_stock
                live_loaded = not live_df.empty
                
        elif platform == "TikTok":
            tt_act = st.file_uploader("TikTok Active listings stock file", type=["xlsx", "xls", "csv"], key="live_tt_act")
            tt_inact = st.file_uploader("TikTok Inactive listings stock file", type=["xlsx", "xls", "csv"], key="live_tt_inact")
            if tt_act or tt_inact:
                live_df = load_tiktok(tt_act, tt_inact)
                live_loaded = not live_df.empty

    st.markdown("---")
    st.markdown("### Upload Target Listings Sheet")
    input_mode = st.radio(
        "Upload Sheet Mode",
        ["File Upload (Excel/CSV)", "Google Sheets Link"]
    )
    
    upload_dfs = {}
    if input_mode == "File Upload (Excel/CSV)":
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
        if gsheet_url:
            try:
                with st.spinner("Downloading Google Sheet..."):
                    df = load_google_sheet(gsheet_url)
                    upload_dfs["Google Sheet"] = df
            except Exception as e:
                st.error(f"Failed to fetch sheet: {e}. Check if view permissions are open.")

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
        
        check_live_images = False
        if qc_stage == "Post QC":
            check_live_images = st.checkbox("Live HTTP Image Check", value=False)

# ── Main Content Area ────────────────────────────────────────────────────────
if not upload_dfs:
    st.info("👈 Please load your references and primary Upload Sheet in the sidebar control panel to begin.")
    
elif not content_file or not zecom_file:
    st.warning("⚠️ Reference files missing! Please upload both Content File and zEcom File in the sidebar.")
    
else:
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
    if st.button("🚀 Run QC Validation", type="primary", use_container_width=True):
        with st.spinner("Loading references and running validations..."):
            try:
                # 1. Parse Reference DataFrames
                content_df = load_content(content_file)
                zecom_df = load_zecom(zecom_file, country)
                
                # 2. Standardize target sheets
                all_standardized = []
                for fn, df in upload_dfs.items():
                    std_df = standardize_dataframe(df, manual_mapping, source_name=fn)
                    all_standardized.append(std_df)
                combined_df = pd.concat(all_standardized, ignore_index=True)
                
                # 3. Execute validation rules
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
                
                # Store in session state
                st.session_state.val_df = val_df
                st.session_state.exc_df = exc_df
                st.session_state.logs = logs
                st.session_state.ran_validation = True
                
                # Reset comparison state for new run
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
        passed_count = sum(val_df["_qc_status"] == "Passed")
        warning_count = sum(val_df["_qc_status"] == "Warning")
        failed_count = sum(val_df["_qc_status"] == "Failed")
        
        kpi_cols = st.columns(4)
        with kpi_cols[0]:
            st.markdown(f'<div class="metric-card metric-total"><div class="metric-title">Total Audited</div><div class="metric-value">{total_records}</div></div>', unsafe_allow_html=True)
        with kpi_cols[1]:
            st.markdown(f'<div class="metric-card metric-passed"><div class="metric-title">Passed (Clean)</div><div class="metric-value">{passed_count}</div></div>', unsafe_allow_html=True)
        with kpi_cols[2]:
            st.markdown(f'<div class="metric-card metric-warnings"><div class="metric-title">Warnings Flagged</div><div class="metric-value">{warning_count}</div></div>', unsafe_allow_html=True)
        with kpi_cols[3]:
            st.markdown(f'<div class="metric-card metric-failed"><div class="metric-title">Failed (Critical Errors)</div><div class="metric-value">{failed_count}</div></div>', unsafe_allow_html=True)
            
        tabs = [
            "📊 Dashboard & Data View",
            "❌ Exceptions Report",
            "📜 Execution Logs"
        ]
        
        # Add Comparison tab if in Post QC stage
        if qc_stage == "Post QC":
            tabs.insert(2, "🔄 Live Listing Sync Audit")
            
        tab_list = st.tabs(tabs)
        
        # Mapping tabs to views
        tab_dashboard = tab_list[0]
        tab_exceptions = tab_list[1]
        
        if qc_stage == "Post QC":
            tab_live_compare = tab_list[2]
            tab_logs = tab_list[3]
        else:
            tab_logs = tab_list[2]
            tab_live_compare = None
        
        with tab_dashboard:
            db_col1, db_col2 = st.columns([1, 2])
            with db_col1:
                st.markdown("#### Exception Breakdown by Field")
                if exc_df.empty:
                    st.success("🎉 No exceptions found! All listings are clean.")
                else:
                    field_counts = exc_df["Field"].value_counts().reset_index()
                    field_counts.columns = ["QC Field", "Issues Count"]
                    st.dataframe(field_counts, use_container_width=True, hide_index=True)
                    
                    st.markdown("#### Severity Summary")
                    sev_counts = exc_df["Severity"].value_counts().reset_index()
                    sev_counts.columns = ["Severity", "Issues Count"]
                    st.dataframe(sev_counts, use_container_width=True, hide_index=True)

            with db_col2:
                st.markdown("#### Validated Dataset Preview")
                preview_df = val_df.copy()
                disp_mapping = {
                    "_original_row_number": "Row",
                    "_source_file": "Source",
                    "_qc_status": "Status",
                    "_qc_errors": "Errors",
                    "_qc_warnings": "Warnings",
                    "article_number": "Article No",
                    "sku": "SKU (EAN)",
                    "ecommerce_status": "Ecom Status",
                    "product_name": "Product Name"
                }
                preview_df = preview_df.rename(columns=disp_mapping)
                cols_to_disp = ["Source", "Row", "Status", "Errors", "Warnings", "Article No", "SKU (EAN)", "Product Name", "price", "quantity"]
                cols_to_disp = [c for c in cols_to_disp if c in preview_df.columns]
                
                st.dataframe(preview_df[cols_to_disp].head(500), use_container_width=True, hide_index=True)
                
            st.markdown("#### 📥 Download Validation Reports")
            excel_data = generate_qc_excel_report(val_df, exc_df, qc_stage)
            
            c1, c2 = st.columns(2)
            with c1:
                st.download_button(
                    label="📥 Download Detailed Excel QC Report",
                    data=excel_data,
                    file_name=f"Listing_QC_Report_{qc_stage}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            with c2:
                csv_buffer = io.StringIO()
                exc_df.to_csv(csv_buffer, index=False)
                st.download_button(
                    label="📥 Download Exceptions CSV",
                    data=csv_buffer.getvalue(),
                    file_name=f"QC_Exceptions_{qc_stage}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )

        with tab_exceptions:
            st.markdown("#### ❌ Flagged Exceptions & Warnings")
            if exc_df.empty:
                st.success("🎉 All checkmarks passed! No errors or warnings identified.")
            else:
                filter_cols = st.columns(3)
                with filter_cols[0]:
                    sel_severity = st.multiselect("Filter Severity", options=exc_df["Severity"].unique().tolist(), default=exc_df["Severity"].unique().tolist())
                with filter_cols[1]:
                    sel_field = st.multiselect("Filter Field", options=exc_df["Field"].unique().tolist(), default=exc_df["Field"].unique().tolist())
                with filter_cols[2]:
                    sel_file = st.multiselect("Filter Source File", options=exc_df["Source File"].unique().tolist(), default=exc_df["Source File"].unique().tolist())
                
                filtered_exc = exc_df[
                    exc_df["Severity"].isin(sel_severity) & 
                    exc_df["Field"].isin(sel_field) & 
                    exc_df["Source File"].isin(sel_file)
                ]
                st.markdown(f"Displaying **{len(filtered_exc)}** of **{len(exc_df)}** exceptions:")
                st.dataframe(filtered_exc, use_container_width=True, hide_index=True)

        if tab_live_compare is not None:
            with tab_live_compare:
                st.markdown("#### 🔄 Live Store Listing Sync Audit")
                st.markdown(f"Compare your uploaded listing sheet against live listings for **{channel}**.")
                
                if not live_loaded:
                    st.info(f"💡 Please upload the live listings file in the sidebar under **Upload Marketplace Files ({channel})** to compare.")
                else:
                    st.success(f"✅ Live listing file loaded containing {len(live_df)} records.")
                    
                    if st.button("🔄 Execute Comparison Audit", type="primary", key="btn_run_compare"):
                        with st.spinner("Running comparison logic..."):
                            # Standardize source data from the active validation run
                            standardized_source = val_df.copy()
                            
                            # Standardize live data
                            # Note: live_df already loaded with correct keys (SKU, MP Stock, MP Status, MP Price)
                            # Match key is SKU
                            comp_df, comp_metrics = compare_source_and_live(
                                standardized_source,
                                live_df,
                                match_column="sku"
                            )
                            
                            st.session_state.comp_df = comp_df
                            st.session_state.comp_metrics = comp_metrics
                            st.session_state.ran_comparison = True
                            
                    if st.session_state.ran_comparison:
                        st.markdown("---")
                        st.markdown("##### Comparison Summary")
                        
                        comp_df = st.session_state.comp_df
                        comp_metrics = st.session_state.comp_metrics
                        
                        c_kpis = st.columns(5)
                        labels = list(comp_metrics.keys())
                        vals = list(comp_metrics.values())
                        theme_colors = ["#38bdf8", "#34d399", "#f87171", "#fbbf24", "#a78bfa"]
                        
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

        with tab_logs:
            st.markdown("#### 📜 Validation Execution Audit Log")
            log_str = "\n".join(logs)
            st.markdown(f'<div class="log-box">{log_str.replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)
            
            st.download_button(
                label="📥 Download Text Logs",
                data=log_str,
                file_name=f"QC_Validation_Logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain"
            )

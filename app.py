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
    CANONICAL_LABELS
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

if "ran_comparison" not in st.session_state:
    st.session_state.ran_comparison = False
if "comp_df" not in st.session_state:
    st.session_state.comp_df = pd.DataFrame()
if "comp_metrics" not in st.session_state:
    st.session_state.comp_metrics = {}

# ── Sidebar Configurations ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### QC Control Panel")
    qc_stage = st.selectbox(
        "QC Process Stage",
        ["Internal QC", "Post QC"],
        help="Internal QC validates pre-listing fields. Post QC includes image links and size charts."
    )
    st.session_state.qc_stage = qc_stage

    input_mode = st.radio(
        "Data Source Mode",
        ["File Upload (Excel/CSV)", "Google Sheets Link"]
    )

    # Allowed Value Overrides
    with st.expander("Advanced Settings"):
        custom_genders_str = st.text_input(
            "Allowed Genders",
            value=", ".join(ALLOWED_GENDERS),
            help="Comma-separated list of allowed genders."
        )
        custom_genders = [g.strip().lower() for g in custom_genders_str.split(",") if g.strip()]
        
        custom_statuses_str = st.text_input(
            "Allowed Ecom Statuses",
            value=", ".join(ALLOWED_STATUSES),
            help="Comma-separated list of allowed listing statuses."
        )
        custom_statuses = [s.strip().lower() for s in custom_statuses_str.split(",") if s.strip()]
        
        check_live_images = False
        if qc_stage == "Post QC":
            check_live_images = st.checkbox(
                "Live HTTP Image Check",
                value=False,
                help="Check if image URLs are active and reachable. (Might slow down bulk loading)."
            )

    st.markdown("---")
    st.markdown("### Upload Source Files")
    
    source_dfs = {}
    
    if input_mode == "File Upload (Excel/CSV)":
        uploaded_files = st.file_uploader(
            "Upload Product Listings",
            type=["xlsx", "xls", "csv"],
            accept_multiple_files=True,
            key="src_uploader"
        )
        if uploaded_files:
            for f in uploaded_files:
                try:
                    df = load_file_to_df(f)
                    source_dfs[f.name] = df
                except Exception as e:
                    st.error(f"Error loading {f.name}: {e}")
                    
    else:
        gsheet_url = st.text_input(
            "Google Sheets Sharing URL",
            placeholder="https://docs.google.com/spreadsheets/d/..."
        )
        if gsheet_url:
            try:
                with st.spinner("Downloading Google Sheet..."):
                    df = load_google_sheet(gsheet_url)
                    source_dfs["Google Sheet"] = df
            except Exception as e:
                st.error(f"Failed to fetch sheet: {e}. Ensure the sheet has 'Anyone with link' viewer access.")

# ── Main Content Area ────────────────────────────────────────────────────────
if not source_dfs:
    st.info("👈 Please upload product listing files or paste a Google Sheets URL in the sidebar to begin.")
    
else:
    # ── Column Mapping Step ───────────────────────────────────────────────────
    st.subheader("📋 Column Mapping Alignment")
    st.markdown("Align the columns in your uploaded files to the standard QC data fields:")
    
    # Collect all headers across uploaded files
    all_headers = []
    for fn, df in source_dfs.items():
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
        
        # Determine index in selectbox
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
        with st.spinner("Standardizing files and running QC rules..."):
            all_standardized = []
            
            for fn, df in source_dfs.items():
                std_df = standardize_dataframe(df, manual_mapping, source_name=fn)
                all_standardized.append(std_df)
                
            combined_df = pd.concat(all_standardized, ignore_index=True)
            
            # Run validations
            exc_df, val_df, logs = validate_dataframe(
                combined_df, 
                qc_stage=qc_stage,
                check_live_images=check_live_images,
                allowed_genders=custom_genders,
                allowed_statuses=custom_statuses
            )
            
            # Store in session state
            st.session_state.val_df = val_df
            st.session_state.exc_df = exc_df
            st.session_state.logs = logs
            st.session_state.ran_validation = True

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
        
        # Display KPI cards using styled HTML
        kpi_cols = st.columns(4)
        with kpi_cols[0]:
            st.markdown(f"""
            <div class="metric-card metric-total">
                <div class="metric-title">Total Audited</div>
                <div class="metric-value">{total_records}</div>
            </div>
            """, unsafe_allow_html=True)
        with kpi_cols[1]:
            st.markdown(f"""
            <div class="metric-card metric-passed">
                <div class="metric-title">Passed (Clean)</div>
                <div class="metric-value">{passed_count}</div>
            </div>
            """, unsafe_allow_html=True)
        with kpi_cols[2]:
            st.markdown(f"""
            <div class="metric-card metric-warnings">
                <div class="metric-title">Warnings Flagged</div>
                <div class="metric-value">{warning_count}</div>
            </div>
            """, unsafe_allow_html=True)
        with kpi_cols[3]:
            st.markdown(f"""
            <div class="metric-card metric-failed">
                <div class="metric-title">Failed (Critical Errors)</div>
                <div class="metric-value">{failed_count}</div>
            </div>
            """, unsafe_allow_html=True)
            
        # Tabs for detailed layout
        tab_dashboard, tab_exceptions, tab_live_compare, tab_logs = st.tabs([
            "📊 Dashboard & Data View",
            "❌ Exceptions Report",
            "🔄 Live Listing Sync Audit",
            "📜 Execution Logs"
        ])
        
        with tab_dashboard:
            # Layout
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
                # Map statuses to badges for preview
                preview_df = val_df.copy()
                # Clean up column names for display
                disp_mapping = {
                    "_original_row_number": "Row",
                    "_source_file": "Source",
                    "_qc_status": "Status",
                    "_qc_errors": "Errors",
                    "_qc_warnings": "Warnings",
                    "article_number": "Article No",
                    "ecommerce_status": "Ecom Status",
                    "product_name": "Product Name"
                }
                preview_df = preview_df.rename(columns=disp_mapping)
                cols_to_disp = ["Source", "Row", "Status", "Errors", "Warnings", "Article No", "Product Name", "price", "quantity"]
                # Keep only existing columns
                cols_to_disp = [c for c in cols_to_disp if c in preview_df.columns]
                
                st.dataframe(preview_df[cols_to_disp].head(500), use_container_width=True, hide_index=True)
                
            # Export Reports
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
                # CSV Export of exceptions
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
                # Add filters
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
                
                # Render table
                st.markdown(f"Displaying **{len(filtered_exc)}** of **{len(exc_df)}** exceptions:")
                
                # Style table rows or columns
                st.dataframe(filtered_exc, use_container_width=True, hide_index=True)

        with tab_live_compare:
            st.markdown("#### 🔄 Live Store Listing Sync Audit")
            st.markdown("Compare your master/validated source sheet against live listings exported from Shopee, Lazada, or Zalora.")
            
            # Setup inputs for live listings
            comp_cols = st.columns(2)
            with comp_cols[0]:
                live_file = st.file_uploader(
                    "Upload Live Listings Export (Excel/CSV)",
                    type=["xlsx", "xls", "csv"],
                    key="live_uploader"
                )
            with comp_cols[1]:
                live_url = st.text_input(
                    "Live Listings Google Sheets URL",
                    placeholder="https://docs.google.com/spreadsheets/d/...",
                    key="live_url_box"
                )
                
            # Alignment configuration
            if live_file or live_url:
                try:
                    if live_file:
                        live_df_raw = load_file_to_df(live_file)
                        live_name = live_file.name
                    else:
                        with st.spinner("Downloading live listing sheet..."):
                            live_df_raw = load_google_sheet(live_url)
                            live_name = "Live Google Sheet"
                            
                    st.success(f"Successfully loaded Live Listings File: {live_name} ({len(live_df_raw)} records)")
                    
                    # Align columns for the Live File
                    st.markdown("##### Align Live File Columns")
                    live_headers = live_df_raw.columns.tolist()
                    live_auto_maps = auto_map_columns(live_headers)
                    
                    l_cols = st.columns(3)
                    live_mapping = {}
                    
                    # Map same fields
                    for i, canonical in enumerate(fields_to_map):
                        l_col_sel = l_cols[i % 3]
                        l_default_val = live_auto_maps.get(canonical)
                        
                        l_options = ["-- Skip / Missing --"] + live_headers
                        l_default_idx = 0
                        if l_default_val in live_headers:
                            l_default_idx = l_options.index(l_default_val)
                            
                        with l_col_sel:
                            l_mapped_col = st.selectbox(
                                f"Live {CANONICAL_LABELS[canonical]}",
                                options=l_options,
                                index=l_default_idx,
                                key=f"live_map_{canonical}"
                            )
                            live_mapping[canonical] = None if l_mapped_col == "-- Skip / Missing --" else l_mapped_col
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🔄 Execute Comparison Audit", type="primary"):
                        with st.spinner("Running comparison logic..."):
                            # Standardize source data from the active validation run
                            standardized_source = val_df.copy()
                            
                            # Standardize live data
                            standardized_live = standardize_dataframe(live_df_raw, live_mapping, source_name=live_name)
                            
                            # Run comparison
                            comp_df, comp_metrics = compare_source_and_live(
                                standardized_source,
                                standardized_live,
                                match_column="article_number"
                            )
                            
                            st.session_state.comp_df = comp_df
                            st.session_state.comp_metrics = comp_metrics
                            st.session_state.ran_comparison = True
                            
                except Exception as e:
                    st.error(f"Failed to process live listings file: {e}")
                    import traceback
                    st.error(traceback.format_exc())
            else:
                st.info("Upload a live product listing export to run comparison checks.")

            # Show Comparison Results
            if st.session_state.ran_comparison:
                st.markdown("---")
                st.markdown("##### Comparison Summary")
                
                comp_df = st.session_state.comp_df
                comp_metrics = st.session_state.comp_metrics
                
                c_kpis = st.columns(5)
                labels = list(comp_metrics.keys())
                vals = list(comp_metrics.values())
                
                # Styles for comparison card metrics
                theme_colors = ["#38bdf8", "#34d399", "#f87171", "#fbbf24", "#a78bfa"]
                
                for idx in range(len(labels)):
                    with c_kpis[idx]:
                        st.markdown(f"""
                        <div class="metric-card" style="border-top: 4px solid {theme_colors[idx]};">
                            <div class="metric-title">{labels[idx]}</div>
                            <div class="metric-value" style="color: {theme_colors[idx]};">{vals[idx]}</div>
                        </div>
                        """, unsafe_allow_html=True)
                
                st.markdown("##### Detailed Discrepancy Table")
                mismatches_only = comp_df[comp_df["Match Status"] != "Passed"]
                
                if mismatches_only.empty:
                    st.success("🎉 Perfect Sync! All compared attributes match perfectly between source and live files.")
                else:
                    st.markdown(f"Found **{len(mismatches_only)}** discrepancies between sheets:")
                    st.dataframe(mismatches_only, use_container_width=True, hide_index=True)
                
                # Export Comparison
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
            
            # Simple text download for logs
            st.download_button(
                label="📥 Download Text Logs",
                data=log_str,
                file_name=f"QC_Validation_Logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain"
            )

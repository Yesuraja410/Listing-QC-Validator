import io
import datetime
import pandas as pd
from typing import Dict, Tuple

def generate_qc_excel_report(val_df: pd.DataFrame, exc_df: pd.DataFrame, qc_stage: str) -> bytes:
    """
    Generates a beautifully formatted Excel report for validation results.
    Includes:
      - Sheet 1: Executive Dashboard (Summary metrics & Metadata)
      - Sheet 2: Detailed Exceptions (List of all Errors and Warnings)
      - Sheet 3: Validated Dataset (Full user data with validation flags)
    Returns:
      Bytes content of the generated Excel workbook.
    """
    output = io.BytesIO()
    
    # Pre-process tables for export (drop internal underscore columns from display sheets, except tracking)
    # On Sheet 3 (Validated Data), we want to make it look clean: rename tracking columns to user-friendly names
    clean_val_df = val_df.copy()
    col_mapping = {
        "_original_row_number": "Excel Row",
        "_source_file": "Source File",
        "_qc_status": "QC Status",
        "_qc_errors": "Total Errors",
        "_qc_warnings": "Total Warnings",
        "_qc_details": "Validation Logs"
    }
    clean_val_df = clean_val_df.rename(columns=col_mapping)
    
    # Reorder columns slightly so tracking info is near the front
    tracking_cols = ["Source File", "Excel Row", "QC Status", "Total Errors", "Total Warnings", "Validation Logs"]
    other_cols = [c for c in clean_val_df.columns if c not in tracking_cols and not c.startswith("_")]
    clean_val_df = clean_val_df[tracking_cols + other_cols]

    # Calculate metrics for the dashboard
    total_records = len(val_df)
    passed_count = sum(val_df["_qc_status"] == "Passed")
    warning_count = sum(val_df["_qc_status"] == "Warning")
    failed_count = sum(val_df["_qc_status"] == "Failed")
    pass_rate = (passed_count / total_records * 100) if total_records > 0 else 0.0
    
    summary_data = {
        "Metric": [
            "Total Records Validated",
            "Passed (No Errors/Warnings)",
            "Warnings Flagged",
            "Failed (Critical Errors)",
            "Pass Rate"
        ],
        "Count / Value": [
            total_records,
            passed_count,
            warning_count,
            failed_count,
            f"{pass_rate:.2f}%"
        ]
    }
    summary_df = pd.DataFrame(summary_data)
    
    # Metadata info
    metadata_data = {
        "Configuration Details": [
            "Validation Run Date",
            "QC Verification Stage",
            "Target Files Processed",
            "Status"
        ],
        "Value": [
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            qc_stage,
            ", ".join(val_df["_source_file"].unique()),
            "Complete"
        ]
    }
    metadata_df = pd.DataFrame(metadata_data)

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook = writer.book
        
        # ── Color Palettes & Formats ──────────────────────────────────────────
        # Fonts: Segoe UI, Arial
        header_fmt = workbook.add_format({
            'bold': True,
            'font_name': 'Segoe UI',
            'font_color': '#ffffff',
            'bg_color': '#1e3a8a', # Dark navy
            'border': 1,
            'border_color': '#d1d5db',
            'align': 'left',
            'valign': 'vcenter'
        })
        
        title_fmt = workbook.add_format({
            'bold': True,
            'font_name': 'Segoe UI',
            'font_size': 16,
            'font_color': '#1e3a8a'
        })
        
        subtitle_fmt = workbook.add_format({
            'italic': True,
            'font_name': 'Segoe UI',
            'font_size': 10,
            'font_color': '#4b5563'
        })
        
        standard_fmt = workbook.add_format({
            'font_name': 'Segoe UI',
            'font_size': 10,
            'border': 1,
            'border_color': '#e5e7eb',
            'align': 'left'
        })
        
        # Color codes for cells
        red_fill = workbook.add_format({
            'font_name': 'Segoe UI',
            'font_size': 10,
            'bg_color': '#fee2e2', # Light red
            'font_color': '#991b1b', # Dark red
            'border': 1,
            'border_color': '#fca5a5'
        })
        
        yellow_fill = workbook.add_format({
            'font_name': 'Segoe UI',
            'font_size': 10,
            'bg_color': '#fef3c7', # Light yellow
            'font_color': '#92400e', # Dark gold
            'border': 1,
            'border_color': '#fde047'
        })
        
        green_fill = workbook.add_format({
            'font_name': 'Segoe UI',
            'font_size': 10,
            'bg_color': '#d1fae5', # Light green
            'font_color': '#065f46', # Dark green
            'border': 1,
            'border_color': '#6ee7b7'
        })

        # ── Sheet 1: Dashboard ────────────────────────────────────────────────
        summary_df.to_excel(writer, sheet_name="Dashboard", startrow=4, index=False)
        metadata_df.to_excel(writer, sheet_name="Dashboard", startrow=12, index=False)
        
        ws_dash = writer.sheets["Dashboard"]
        ws_dash.write("A2", "LISTING QC VALIDATION DASHBOARD", title_fmt)
        ws_dash.write("A3", f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", subtitle_fmt)
        
        # Formats
        ws_dash.set_column("A:A", 30)
        ws_dash.set_column("B:B", 40)
        
        # Apply headers
        ws_dash.write_row("A5", summary_df.columns, header_fmt)
        ws_dash.write_row("A13", metadata_df.columns, header_fmt)
        
        for r in range(len(summary_df)):
            row_idx = 5 + r
            ws_dash.write(row_idx, 0, summary_df.iloc[r, 0], standard_fmt)
            val = summary_df.iloc[r, 1]
            
            # Format depending on status type
            if r == 1: # Passed
                ws_dash.write(row_idx, 1, val, green_fill)
            elif r == 2: # Warnings
                ws_dash.write(row_idx, 1, val, yellow_fill)
            elif r == 3: # Failed
                ws_dash.write(row_idx, 1, val, red_fill)
            else:
                ws_dash.write(row_idx, 1, val, standard_fmt)

        for r in range(len(metadata_df)):
            row_idx = 13 + r
            ws_dash.write(row_idx, 0, metadata_df.iloc[r, 0], standard_fmt)
            ws_dash.write(row_idx, 1, metadata_df.iloc[r, 1], standard_fmt)
            
        ws_dash.hide_gridlines(2) # show gridlines but styled

        # ── Sheet 2: Exceptions ───────────────────────────────────────────────
        exc_df.to_excel(writer, sheet_name="Exceptions", startrow=3, index=False)
        ws_exc = writer.sheets["Exceptions"]
        ws_exc.write("A1", "CRITICAL LISTING EXCEPTIONS REPORT", title_fmt)
        ws_exc.write("A2", "Review flagged errors (listing blocked) and warnings (requires check) below.", subtitle_fmt)
        
        # Headers
        ws_exc.write_row("A4", exc_df.columns, header_fmt)
        
        # Populate and format exceptions rows
        for r in range(len(exc_df)):
            row_idx = 4 + r
            severity = exc_df.iloc[r, 6] # Severity column (Error/Warning)
            
            # Select format based on severity
            row_format = red_fill if severity == "Error" else yellow_fill
            
            for c in range(len(exc_df.columns)):
                val = exc_df.iloc[r, c]
                ws_exc.write(row_idx, c, str(val) if not pd.isna(val) else "", row_format)
                
        # Auto-adjust column widths
        for col_num, col_name in enumerate(exc_df.columns):
            max_len = max(
                exc_df[col_name].astype(str).map(len).max(),
                len(col_name)
            ) + 3
            # Limit width to 50
            ws_exc.set_column(col_num, col_num, min(max(max_len, 10), 50))
            
        ws_exc.autofilter(3, 0, len(exc_df) + 3, len(exc_df.columns) - 1)
        ws_exc.hide_gridlines(2)

        # ── Sheet 3: Validated Data ───────────────────────────────────────────
        clean_val_df.to_excel(writer, sheet_name="Validated Data", startrow=3, index=False)
        ws_val = writer.sheets["Validated Data"]
        ws_val.write("A1", "STANDARDIZED & VALIDATED DATASET", title_fmt)
        ws_val.write("A2", "Full product rows with appended QC audit markers.", subtitle_fmt)
        
        # Headers
        ws_val.write_row("A4", clean_val_df.columns, header_fmt)
        
        # Populate and style validated data
        for r in range(len(clean_val_df)):
            row_idx = 4 + r
            status = clean_val_df.iloc[r, 2] # QC Status column ('Passed', 'Warning', 'Failed')
            
            if status == "Passed":
                row_format = green_fill
            elif status == "Warning":
                row_format = yellow_fill
            else:
                row_format = red_fill
                
            for c in range(len(clean_val_df.columns)):
                val = clean_val_df.iloc[r, c]
                ws_val.write(row_idx, c, str(val) if not pd.isna(val) else "", row_format)
                
        # Auto-adjust column widths
        for col_num, col_name in enumerate(clean_val_df.columns):
            max_len = max(
                clean_val_df[col_name].astype(str).map(len).max(),
                len(col_name)
            ) + 3
            ws_val.set_column(col_num, col_num, min(max(max_len, 10), 40))
            
        ws_val.autofilter(3, 0, len(clean_val_df) + 3, len(clean_val_df.columns) - 1)
        ws_val.hide_gridlines(2)

    return output.getvalue()


def generate_comparison_excel_report(comp_df: pd.DataFrame, summary_metrics: Dict) -> bytes:
    """
    Generates a formatted Excel report highlighting discrepancies between source data and live store listings.
    Includes:
      - Sheet 1: Audit Summary (Summary metrics)
      - Sheet 2: Discrepancy details
    """
    output = io.BytesIO()
    
    # Prepare summary df
    summary_data = {
        "Audit Checkpoint": list(summary_metrics.keys()),
        "Count of Records": list(summary_metrics.values())
    }
    summary_df = pd.DataFrame(summary_data)

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook = writer.book
        
        # Formats
        header_fmt = workbook.add_format({
            'bold': True,
            'font_name': 'Segoe UI',
            'font_color': '#ffffff',
            'bg_color': '#0f172a', # Charcoal
            'border': 1,
            'border_color': '#d1d5db',
            'align': 'left',
            'valign': 'vcenter'
        })
        
        title_fmt = workbook.add_format({
            'bold': True,
            'font_name': 'Segoe UI',
            'font_size': 15,
            'font_color': '#0f172a'
        })
        
        subtitle_fmt = workbook.add_format({
            'italic': True,
            'font_name': 'Segoe UI',
            'font_size': 10,
            'font_color': '#6b7280'
        })
        
        standard_fmt = workbook.add_format({
            'font_name': 'Segoe UI',
            'font_size': 10,
            'border': 1,
            'border_color': '#e5e7eb',
            'align': 'left'
        })
        
        red_fill = workbook.add_format({
            'font_name': 'Segoe UI',
            'font_size': 10,
            'bg_color': '#fee2e2',
            'font_color': '#991b1b',
            'border': 1,
            'border_color': '#fca5a5'
        })
        
        yellow_fill = workbook.add_format({
            'font_name': 'Segoe UI',
            'font_size': 10,
            'bg_color': '#fef3c7',
            'font_color': '#92400e',
            'border': 1,
            'border_color': '#fde047'
        })
        
        green_fill = workbook.add_format({
            'font_name': 'Segoe UI',
            'font_size': 10,
            'bg_color': '#d1fae5',
            'font_color': '#065f46',
            'border': 1,
            'border_color': '#6ee7b7'
        })

        # ── Sheet 1: Summary ──────────────────────────────────────────────────
        summary_df.to_excel(writer, sheet_name="Audit Summary", startrow=4, index=False)
        ws_sum = writer.sheets["Audit Summary"]
        ws_sum.write("A1", "LIVE LISTING COMPARISON AUDIT SUMMARY", title_fmt)
        ws_sum.write("A2", f"Comparison Run Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", subtitle_fmt)
        
        ws_sum.set_column("A:A", 35)
        ws_sum.set_column("B:B", 25)
        
        ws_sum.write_row("A5", summary_df.columns, header_fmt)
        
        for r in range(len(summary_df)):
            row_idx = 5 + r
            ws_sum.write(row_idx, 0, summary_df.iloc[r, 0], standard_fmt)
            val = summary_df.iloc[r, 1]
            
            if r == 1: # Fully matched
                ws_sum.write(row_idx, 1, val, green_fill)
            elif r == 2: # Mismatches
                ws_sum.write(row_idx, 1, val, red_fill)
            elif r in [3, 4]: # Missing or extra
                ws_sum.write(row_idx, 1, val, yellow_fill)
            else:
                ws_sum.write(row_idx, 1, val, standard_fmt)
                
        ws_sum.hide_gridlines(2)

        # ── Sheet 2: Discrepancy Details ──────────────────────────────────────
        comp_df.to_excel(writer, sheet_name="Discrepancy Details", startrow=3, index=False)
        ws_det = writer.sheets["Discrepancy Details"]
        ws_det.write("A1", "DETAILED DISCREPANCY COMPARISON", title_fmt)
        ws_det.write("A2", "Complete list of mismatches and listing discrepancies between source master and store listings.", subtitle_fmt)
        
        ws_det.write_row("A4", comp_df.columns, header_fmt)
        
        for r in range(len(comp_df)):
            row_idx = 4 + r
            status = comp_df.iloc[r, 6] # Match Status column ('Passed', 'Mismatch', 'Failed (Missing Live)', 'Warning (Extra Live)')
            
            if "Passed" in status:
                row_format = green_fill
            elif "Mismatch" in status or "Failed" in status:
                row_format = red_fill
            else:
                row_format = yellow_fill
                
            for c in range(len(comp_df.columns)):
                val = comp_df.iloc[r, c]
                ws_det.write(row_idx, c, str(val) if not pd.isna(val) else "", row_format)
                
        for col_num, col_name in enumerate(comp_df.columns):
            max_len = max(
                comp_df[col_name].astype(str).map(len).max(),
                len(col_name)
            ) + 3
            ws_det.set_column(col_num, col_num, min(max(max_len, 10), 45))
            
        ws_det.autofilter(3, 0, len(comp_df) + 3, len(comp_df.columns) - 1)
        ws_det.hide_gridlines(2)

    return output.getvalue()

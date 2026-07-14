import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import numpy as np
from threading import Thread

# Import local processing modules
from utils.file_loaders import (
    load_file_to_df,
    load_excel_all_sheets,
    process_live_files,
    load_content,
    load_zecom,
    auto_map_columns,
    standardize_dataframe,
    load_google_sheet
)
from utils.validators import validate_dataframe, compare_source_and_live
from utils.report_generator import (
    generate_qc_excel_report,
    generate_comparison_excel_report
)
import io

class FileWrapper:
    def __init__(self, filepath):
        self.filepath = filepath
        self.name = os.path.basename(filepath)
        with open(filepath, 'rb') as f:
            self.bytes = f.read()
        self._io = io.BytesIO(self.bytes)
        
    def read(self, *args, **kwargs):
        return self._io.read(*args, **kwargs)
        
    def seek(self, *args, **kwargs):
        return self._io.seek(*args, **kwargs)

class ListingQCGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Listing QC Validator - Desktop Edition")
        self.root.geometry("800x650")
        self.root.minsize(700, 550)
        
        # Configure styles
        style = ttk.Style()
        style.theme_use("vista" if "vista" in style.theme_names() else "clam")
        
        # File paths variables
        self.master_file_path = tk.StringVar()
        self.live_file_path = tk.StringVar()
        self.content_ref_path = tk.StringVar()
        self.zecom_ref_path = tk.StringVar()
        self.qc_stage = tk.StringVar(value="Internal QC")
        self.channel = tk.StringVar(value="Shopee PH")
        
        # Create Layout
        self.create_widgets()
        
    def create_widgets(self):
        # Main Frame
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header Label
        header = tk.Label(
            main_frame, 
            text="Listing QC Validation & Sync Tool", 
            font=("Helvetica", 16, "bold"),
            fg="#1A365D"
        )
        header.pack(anchor=tk.W, pady=(0, 10))
        
        # Config Frame
        config_frame = ttk.LabelFrame(main_frame, text=" 1. Configuration ", padding="10")
        config_frame.pack(fill=tk.X, pady=5)
        
        # QC Stage Selector
        ttk.Label(config_frame, text="QC Stage:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.stage_combo = ttk.Combobox(
            config_frame, 
            textvariable=self.qc_stage, 
            values=["Internal QC", "Post QC"], 
            state="readonly",
            width=15
        )
        self.stage_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        self.stage_combo.bind("<<ComboboxSelected>>", self.on_stage_changed)
        
        # Channel Selector
        ttk.Label(config_frame, text="Channel:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        channels = [
            "Shopee PH", "Shopee SG", "Shopee MY",
            "Lazada PH", "Lazada SG", "Lazada MY",
            "Zalora PH", "Zalora SG", "Zalora MY",
            "TikTok PH", "TikTok SG", "TikTok MY"
        ]
        self.channel_combo = ttk.Combobox(
            config_frame, 
            textvariable=self.channel, 
            values=channels, 
            state="readonly",
            width=15
        )
        self.channel_combo.grid(row=0, column=3, sticky=tk.W, padx=5, pady=5)
        
        # File Inputs Frame
        self.files_frame = ttk.LabelFrame(main_frame, text=" 2. File Selections ", padding="10")
        self.files_frame.pack(fill=tk.X, pady=5)
        
        # Row 0: Master Upload File
        self.lbl_master = ttk.Label(self.files_frame, text="Master Upload File:")
        self.lbl_master.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.ent_master = ttk.Entry(self.files_frame, textvariable=self.master_file_path, width=60)
        self.ent_master.grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(self.files_frame, text="Browse...", command=self.browse_master).grid(row=0, column=2, padx=5, pady=5)
        
        # Row 1: Live Marketplace File (Hidden initially for Internal QC)
        self.lbl_live = ttk.Label(self.files_frame, text="Live Store Report:")
        self.ent_live = ttk.Entry(self.files_frame, textvariable=self.live_file_path, width=60)
        self.btn_browse_live = ttk.Button(self.files_frame, text="Browse...", command=self.browse_live)
        
        # Row 2: Content Reference File
        ttk.Label(self.files_frame, text="Content Reference:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(self.files_frame, textvariable=self.content_ref_path, width=60).grid(row=2, column=1, padx=5, pady=5)
        ttk.Button(self.files_frame, text="Browse...", command=self.browse_content).grid(row=2, column=2, padx=5, pady=5)
        
        # Row 3: zeCOM Tracking File
        ttk.Label(self.files_frame, text="zeCOM Tracking File:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(self.files_frame, textvariable=self.zecom_ref_path, width=60).grid(row=3, column=1, padx=5, pady=5)
        ttk.Button(self.files_frame, text="Browse...", command=self.browse_zecom).grid(row=3, column=2, padx=5, pady=5)
        
        # Run Button
        self.btn_run = tk.Button(
            main_frame, 
            text="RUN QC VALIDATION", 
            font=("Helvetica", 11, "bold"), 
            bg="#2B6CB0", 
            fg="white", 
            padx=15, 
            pady=8,
            command=self.start_validation_thread
        )
        self.btn_run.pack(pady=10)
        
        # Log Output Frame
        log_frame = ttk.LabelFrame(main_frame, text=" Console Log ", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Scrollbar and text area for logs
        self.log_text = tk.Text(log_frame, wrap=tk.WORD, height=12, font=("Courier", 9))
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)
        
        self.log("Desktop GUI Initialized. Ready for validation.")
        
    def on_stage_changed(self, event=None):
        stage = self.qc_stage.get()
        if stage == "Post QC":
            # Show Live file row
            self.lbl_live.grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
            self.ent_live.grid(row=1, column=1, padx=5, pady=5)
            self.btn_browse_live.grid(row=1, column=2, padx=5, pady=5)
            self.lbl_master.config(text="Target Upload File:")
        else:
            # Hide Live file row
            self.lbl_live.grid_forget()
            self.ent_live.grid_forget()
            self.btn_browse_live.grid_forget()
            self.lbl_master.config(text="Master Upload File:")
            
    def browse_master(self):
        path = filedialog.askopenfilename(filetypes=[("Excel or CSV Files", "*.xlsx *.xls *.csv")])
        if path:
            self.master_file_path.set(path)
            
    def browse_live(self):
        path = filedialog.askopenfilename(filetypes=[("Excel or CSV Files", "*.xlsx *.xls *.csv")])
        if path:
            self.live_file_path.set(path)
            
    def browse_content(self):
        path = filedialog.askopenfilename(filetypes=[("Excel or CSV Files", "*.xlsx *.xls *.csv")])
        if path:
            self.content_ref_path.set(path)
            
    def browse_zecom(self):
        path = filedialog.askopenfilename(filetypes=[("Excel Files", "*.xlsx *.xls")])
        if path:
            self.zecom_ref_path.set(path)
            
    def log(self, message):
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        
    def start_validation_thread(self):
        # Disable run button during execution
        self.btn_run.config(state=tk.DISABLED, bg="#A0AEC0")
        # Run in separate thread to keep UI responsive
        Thread(target=self.run_validation, daemon=True).start()
        
    def run_validation(self):
        try:
            stage = self.qc_stage.get()
            chan = self.channel.get()
            master_file = self.master_file_path.get()
            content_file = self.content_ref_path.get()
            zecom_file = self.zecom_ref_path.get()
            
            # Validation checks on inputs
            if not master_file:
                self.log("[ERROR] Master file selection is required.")
                self.root.after(0, self.reset_run_button)
                return
            if not content_file:
                self.log("[ERROR] Content reference file selection is required.")
                self.root.after(0, self.reset_run_button)
                return
            if not zecom_file:
                self.log("[ERROR] zeCOM tracking file selection is required.")
                self.root.after(0, self.reset_run_button)
                return
                
            self.log(f"Starting {stage} processing for {chan}...")
            
            # 1. Load Reference Files
            self.log("Loading Content database...")
            df_content = load_file_to_df(FileWrapper(content_file), channel=chan)
            
            self.log("Loading zeCOM database...")
            # extract country from channel
            country = "SG"
            if "MY" in chan:
                country = "MY"
            elif "PH" in chan:
                country = "PH"
            df_zecom = load_zecom(FileWrapper(zecom_file), country=country)
            
            if stage == "Internal QC":
                self.log("Loading Master file...")
                if "docs.google.com/spreadsheets" in master_file:
                    df_master = {"Google Sheet": load_google_sheet(master_file, channel=chan)}
                else:
                    df_master = load_excel_all_sheets(FileWrapper(master_file), channel=chan)
                
                # Standardize and combine all sheets from the master file
                all_standardized = []
                for sheet_name, df_sheet in df_master.items():
                    if df_sheet.empty:
                        continue
                    mapping = auto_map_columns(df_sheet, channel=chan)
                    std_df = standardize_dataframe(df_sheet, mapping, source_name=sheet_name)
                    all_standardized.append(std_df)
                    
                if not all_standardized:
                    self.log("[ERROR] No valid data found in any sheet of the master file.")
                    self.root.after(0, self.reset_run_button)
                    return
                combined_master = pd.concat(all_standardized, ignore_index=True)
                
                self.log("Running Internal QC checks...")
                exc_df, val_df, logs = validate_dataframe(
                    combined_master, 
                    qc_stage="Internal QC", 
                    channel=chan,
                    content_df=df_content, 
                    zecom_df=df_zecom, 
                    check_live_images=True
                )
                
                for log_line in logs:
                    self.log(f"  {log_line}")
                    
                # Save report
                output_name = f"Listing_QC_Report_Internal_QC_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                if "docs.google.com/spreadsheets" in master_file:
                    save_dir = os.path.join(os.path.expanduser("~"), "Downloads")
                    if not os.path.exists(save_dir):
                        save_dir = os.getcwd()
                else:
                    save_dir = os.path.dirname(master_file)
                output_path = os.path.join(save_dir, output_name)
                
                self.log(f"Saving Excel report to: {output_path}")
                generate_qc_excel_report(exc_df, val_df, output_path, qc_stage="Internal QC")
                self.log("Validation completed successfully.")
                
            else: # Post QC
                live_file = self.live_file_path.get()
                if not live_file:
                    self.log("[ERROR] Live store report selection is required for Post QC.")
                    self.root.after(0, self.reset_run_button)
                    return
                    
                self.log("Loading Target upload template...")
                if "docs.google.com/spreadsheets" in master_file:
                    df_source = {"Google Sheet": load_google_sheet(master_file, channel=chan)}
                else:
                    df_source = load_excel_all_sheets(FileWrapper(master_file), channel=chan)
                
                # Standardize and combine all sheets from the target upload template
                all_standardized = []
                for sheet_name, df_sheet in df_source.items():
                    if df_sheet.empty:
                        continue
                    mapping = auto_map_columns(df_sheet, channel=chan)
                    std_df = standardize_dataframe(df_sheet, mapping, source_name=sheet_name)
                    all_standardized.append(std_df)
                    
                if not all_standardized:
                    self.log("[ERROR] No valid data found in any sheet of the target upload template.")
                    self.root.after(0, self.reset_run_button)
                    return
                combined_source = pd.concat(all_standardized, ignore_index=True)
                
                self.log("Loading Live marketplace report...")
                df_live = process_live_files([FileWrapper(live_file)], channel=chan)
                
                # Extract SKU maps and build reference maps for Post QC (matching app.py logic)
                from utils.validators import build_content_maps, build_zecom_maps, _clean_sku
                from utils.file_loaders import _normalise_article_no
                
                content_maps = build_content_maps(df_content)
                zecom_maps = build_zecom_maps(df_zecom, chan)
                
                sku_to_article = content_maps[0] if content_maps else {}
                sku_to_gender = content_maps[4] if content_maps else {}
                article_to_launchdate = zecom_maps[0] if zecom_maps else {}
                
                # Fetch live listings dict or product_id for fast lookup
                # Fetch live listings dict or product_id for fast lookup
                is_shopee_or_tiktok = chan and any(p in chan.lower() for p in ["shopee", "tiktok"])
                is_shopee = chan and "shopee" in chan.lower()
                if is_shopee and "product_id" in df_live.columns:
                    df_live["_match_key"] = df_live["product_id"].astype(str).str.strip() + " | " + df_live["color_name"].astype(str).str.strip().str.lower()
                elif is_shopee_or_tiktok and "product_id" in df_live.columns:
                    df_live["_match_key"] = df_live["product_id"].astype(str).str.strip()
                else:
                    df_live["_match_key"] = df_live["sku"].astype(str).str.strip().apply(_clean_sku)
                live_dict = df_live.drop_duplicates(subset=["_match_key"]).set_index("_match_key").to_dict("index")
                
                post_qc_records = []
                for idx, row in combined_source.iterrows():
                    raw_sku = str(row.get("sku", "")).strip()
                    clean_s = _clean_sku(raw_sku)
                    if not clean_s:
                        continue
                    
                    prod_id_val = str(row.get("product_id", "")).strip()
                    if is_shopee and prod_id_val:
                        match_k = prod_id_val + " | " + str(row.get("color_name", "")).strip().lower()
                    elif is_shopee_or_tiktok and prod_id_val:
                        match_k = prod_id_val
                    else:
                        match_k = clean_s
                    
                    ref_art = sku_to_article.get(clean_s, "")
                    norm_art = _normalise_article_no(ref_art)
                    ref_ld = article_to_launchdate.get(norm_art, "")
                    live_row = live_dict.get(match_k, {})
                    gender_val = sku_to_gender.get(clean_s, "")
                    
                    post_qc_records.append({
                        "sku": clean_s,
                        "product_id": prod_id_val,
                        "article_number": ref_art,
                        "launch_date": ref_ld,
                        "ecommerce_status": row.get("ecommerce_status", "Active"),
                        "gender": gender_val,
                        "product_name": row.get("product_name", ""),
                        "color_name": row.get("color_name", ""),
                        "size": row.get("size", ""),
                        "price": row.get("price", "0.0"),
                        "quantity": row.get("quantity", "0"),
                        "images": row.get("images", ""),
                        "size_chart": row.get("size_chart", ""),
                        "_original_row_number": row.get("_original_row_number", idx + 2),
                        "_source_file": row.get("_source_file", "Upload Sheet")
                    })
                    
                if not post_qc_records:
                    self.log("[ERROR] No valid SKUs found in target listing sheet.")
                    self.root.after(0, self.reset_run_button)
                    return
                combined_source_standardized = pd.DataFrame(post_qc_records)
                
                self.log("Executing comparison audits (Target vs Live)...")
                comp_df, summary = compare_source_and_live(
                    combined_source_standardized, 
                    df_live, 
                    match_column="sku", 
                    content_df=df_content, 
                    zecom_df=df_zecom, 
                    channel=chan
                )
                
                self.log(f"  Total variants analyzed: {summary.get('Total SKU variants Parsed', len(comp_df))}")
                self.log(f"  Fully matched items: {summary.get('Fully Matched Items', 0)}")
                self.log(f"  Items with mismatches: {summary.get('Items with Mismatches', 0)}")
                
                # Save report
                output_name = f"Listing_QC_Report_Post_QC_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                if "docs.google.com/spreadsheets" in master_file:
                    save_dir = os.path.join(os.path.expanduser("~"), "Downloads")
                    if not os.path.exists(save_dir):
                        save_dir = os.getcwd()
                else:
                    save_dir = os.path.dirname(master_file)
                output_path = os.path.join(save_dir, output_name)
                
                self.log(f"Saving Comparison Excel report to: {output_path}")
                generate_comparison_excel_report(comp_df, summary, output_path)
                self.log("Post QC comparison completed successfully.")
            
            # Show completion message
            self.root.after(0, lambda: messagebox.showinfo("Success", f"Validation completed!\nReport saved to:\n{output_path}"))
            
        except Exception as e:
            self.log(f"[FATAL ERROR] {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            self.root.after(0, lambda: messagebox.showerror("Execution Error", f"Failed with error: {str(e)}"))
            
        finally:
            self.root.after(0, self.reset_run_button)
            
    def reset_run_button(self):
        self.btn_run.config(state=tk.NORMAL, bg="#2B6CB0")

if __name__ == "__main__":
    root = tk.Tk()
    app = ListingQCGUI(root)
    root.mainloop()

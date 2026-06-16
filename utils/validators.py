import re
import datetime
import pandas as pd
import numpy as np
import requests
from typing import Dict, List, Tuple

# Default allowed values
ALLOWED_GENDERS = ["men", "women", "unisex", "kids", "boys", "girls"]
ALLOWED_STATUSES = ["active", "inactive", "draft", "delisted", "suspended", "live", "on", "off"]

URL_REGEX = re.compile(
    r'^(?:http|ftp)s?://' 
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' 
    r'localhost|' 
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' 
    r'(?::\d+)?' 
    r'(?:/?|[/?]\S+)$', re.IGNORECASE)

def _safe_str(val):
    if val is None:
        return ""
    try:
        if pd.isna(val):
            return ""
    except (TypeError, ValueError):
        pass
    return str(val).strip()

def _clean_sku(val):
    s = _safe_str(val)
    if re.fullmatch(r'\d+\.0', s):
        s = s[:-2]
    return s

def _normalise_article_no(val):
    s = _safe_str(val)
    if not s:
        return ""
    s = s.strip().upper()
    s = re.sub(r'[\s\-]+', '_', s)
    s = s.strip('_')
    return s

def _normalise_status(status):
    s = _safe_str(status).lower()
    if s in ("active", "1", "enabled", "yes", "y", "live", "listed"):
        return "Active"
    if s in ("inactive", "0", "disabled", "no", "n", "delisted", "unlisted", "deleted", "removed"):
        return "Inactive"
    return _safe_str(status)

def is_empty(val) -> bool:
    if pd.isna(val) or val is None:
        return True
    val_str = str(val).strip()
    return val_str == "" or val_str.lower() in ["nan", "null", "<na>", "none"]

def clean_str(val) -> str:
    if is_empty(val):
        return ""
    return str(val).strip()

# ── Reference Mappings Builders ───────────────────────────────────────────────

def build_content_maps(content_df: pd.DataFrame) -> Tuple[Dict[str, str], Dict[str, str], Dict[str, set], Dict[str, str]]:
    """
    Builds lookup tables from Content File:
    1. sku_to_article: SKU -> Article No
    2. sku_to_uksize: SKU -> uk_size
    3. article_to_uksizes: Article No -> Set of valid UK sizes
    4. sku_to_gender: SKU -> Gender
    """
    sku_to_article = {}
    sku_to_uksize = {}
    article_to_uksizes = {}
    sku_to_gender = {}
    
    if content_df is not None and not content_df.empty:
        has_sku = "SKU" in content_df.columns
        has_art = "Article No" in content_df.columns
        has_uk_size = "uk_size" in content_df.columns
        gender_col = next((c for c in content_df.columns if c.lower() in ["gender", "sex"]), None)
        
        for _, r in content_df.iterrows():
            sku_val = _clean_sku(r.get("SKU")) if has_sku else ""
            art_val = _normalise_article_no(r.get("Article No")) if has_art else ""
            sz_val = _safe_str(r.get("uk_size")).strip() if has_uk_size else ""
            
            if sku_val:
                if art_val:
                    sku_to_article[sku_val] = art_val
                if sz_val:
                    sku_to_uksize[sku_val] = sz_val
                if gender_col:
                    sku_to_gender[sku_val] = _safe_str(r.get(gender_col)).strip()
                    
            if art_val and sz_val:
                if art_val not in article_to_uksizes:
                    article_to_uksizes[art_val] = set()
                article_to_uksizes[art_val].add(sz_val.lower())
                
    return sku_to_article, sku_to_uksize, article_to_uksizes, sku_to_gender


def build_zecom_maps(zecom_df: pd.DataFrame, channel: str) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Builds lookup tables from zEcom File based on target channel platform:
    1. article_to_launchdate: Article No -> Launch Date
    2. article_to_ecomstatus: Article No -> Ecom Status (Active vs Inactive)
    """
    article_to_launchdate = {}
    article_to_ecomstatus = {}
    
    if zecom_df is not None and not zecom_df.empty:
        # e.g., Lazada SG -> Lazada, Shopee PH -> Shopee
        platform = channel.split()[0].lower()
        ecom_col = f"Ecom_{platform.capitalize()}" # Ecom_Lazada, Ecom_Shopee, etc.
        
        has_art = "Article No" in zecom_df.columns
        has_launch = "Launch Date" in zecom_df.columns
        has_ecom = ecom_col in zecom_df.columns
        
        for _, r in zecom_df.iterrows():
            art_val = _normalise_article_no(r.get("Article No"))
            if art_val:
                if has_launch:
                    ld = r.get("Launch Date")
                    if pd.notna(ld) and str(ld).strip() not in ("", "NaT", "nan"):
                        try:
                            article_to_launchdate[art_val] = str(pd.to_datetime(ld).date())
                        except Exception:
                            article_to_launchdate[art_val] = _safe_str(ld)
                    else:
                        article_to_launchdate[art_val] = ""
                        
                if has_ecom:
                    article_to_ecomstatus[art_val] = _safe_str(r.get(ecom_col))
                    
    return article_to_launchdate, article_to_ecomstatus

# ── Row Validation Logic ──────────────────────────────────────────────────────

def validate_row_internal(
    row: pd.Series, 
    idx: int, 
    content_maps: Tuple = (None, None, None, None),
    zecom_maps: Tuple = (None, None),
    allowed_genders: List[str] = ALLOWED_GENDERS, 
    allowed_statuses: List[str] = ALLOWED_STATUSES
) -> List[Dict]:
    """
    Validates a single row for Internal QC with reference lookups.
    """
    exceptions = []
    source_file = row.get("_source_file", "Unknown File")
    row_num = row.get("_original_row_number", idx + 2)
    art_num = clean_str(row.get("article_number", ""))
    norm_art = _normalise_article_no(art_num)
    sku_val = _clean_sku(row.get("sku", ""))
    prod_name = clean_str(row.get("product_name", ""))
    gender = clean_str(row.get("gender", ""))
    size = clean_str(row.get("size", ""))
    ecom_status = clean_str(row.get("ecommerce_status", ""))
    
    sku_to_article, sku_to_uksize, article_to_uksizes, sku_to_gender = content_maps
    article_to_launchdate, article_to_ecomstatus = zecom_maps

    def add_exc(field: str, val, severity: str, msg: str):
        exceptions.append({
            "Source File": source_file,
            "Row Number": row_num,
            "Article Number": art_num if art_num else "MISSING",
            "Product Name": prod_name if prod_name else "MISSING",
            "Field": field,
            "Value": str(val) if not pd.isna(val) else "MISSING",
            "Severity": severity,
            "Message": msg
        })

    # 1. Article Number Basic Check
    if is_empty(row.get("article_number")):
        add_exc("Article Number", row.get("article_number"), "Error", "Article Number is missing.")
    else:
        if not re.match(r"^[a-zA-Z0-9-_]+$", art_num):
            add_exc("Article Number", art_num, "Warning", "Article Number contains special characters. Standard alphanumeric recommended.")

    # 2. SKU Basic Check
    if is_empty(row.get("sku")):
        add_exc("SKU", row.get("sku"), "Error", "SKU (EAN) is missing.")
    else:
        if not re.fullmatch(r'\d{13}', sku_val):
            add_exc("SKU", sku_val, "Warning", "SKU must be exactly 13 digits barcode.")

    # 3. E-commerce Status Basic Check
    if is_empty(row.get("ecommerce_status")):
        add_exc("E-commerce Status", row.get("ecommerce_status"), "Error", "E-commerce Status is missing.")

    # 4. Launch Date Basic Check
    parsed_date = None
    launch_date_raw = row.get("launch_date")
    if is_empty(launch_date_raw):
        add_exc("Launch Date", launch_date_raw, "Error", "Launch Date is missing.")
    else:
        if isinstance(launch_date_raw, (datetime.datetime, datetime.date)):
            parsed_date = launch_date_raw
        else:
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d", "%d-%m-%Y"):
                try:
                    parsed_date = datetime.datetime.strptime(str(launch_date_raw).strip(), fmt).date()
                    break
                except ValueError:
                    continue
            if parsed_date is None:
                try:
                    parsed_date = pd.to_datetime(launch_date_raw).date()
                except Exception:
                    pass
        if parsed_date is None:
            add_exc("Launch Date", launch_date_raw, "Error", "Launch Date has an invalid format. Recommended: YYYY-MM-DD.")

    # 5. Gender Basic Check
    if is_empty(row.get("gender")):
        add_exc("Gender", row.get("gender"), "Error", "Gender is missing.")
    elif gender.lower() not in [g.lower() for g in allowed_genders]:
        add_exc("Gender", gender, "Error", f"Gender '{gender}' is invalid. Allowed: {', '.join(allowed_genders)}.")

    # 6. Product Name vs Gender Keyword Check
    if is_empty(row.get("product_name")):
        add_exc("Product Name", row.get("product_name"), "Error", "Product Name is missing.")
    elif not is_empty(row.get("gender")) and gender.lower() in [g.lower() for g in allowed_genders]:
        gender_low = gender.lower()
        prod_name_low = prod_name.lower()
        
        male_mismatch_keywords = [
            r"\bwomen\b", r"\bwomens\b", r"\bgirl\b", r"\bgirls\b", r"\blady\b", 
            r"\bladies\b", r"\bshe\b", r"\bher\b", r"\bfemale\b", r"\bwoman\b"
        ]
        female_mismatch_keywords = [
            r"\bmen\b", r"\bmens\b", r"\bboy\b", r"\bboys\b", r"\bhim\b", r"\bhis\b", r"\bmale\b"
        ]
        
        if gender_low in ["men", "boys"]:
            for pattern in male_mismatch_keywords:
                if re.search(pattern, prod_name_low):
                    add_exc("Product Name", prod_name, "Error", f"Gender mismatch: Name contains female keyword '{re.sub(r'[^a-zA-Z]', '', pattern)}' but Gender is '{gender}'.")
                    break
        elif gender_low in ["women", "girls"]:
            for pattern in female_mismatch_keywords:
                if re.search(pattern, prod_name_low):
                    add_exc("Product Name", prod_name, "Error", f"Gender mismatch: Name contains male keyword '{re.sub(r'[^a-zA-Z]', '', pattern)}' but Gender is '{gender}'.")
                    break

    # 7. Color Name Basic Check
    if is_empty(row.get("color_name")):
        add_exc("Color Name", row.get("color_name"), "Error", "Color Name is missing.")

    # 8. Size Basic Check
    if is_empty(row.get("size")):
        add_exc("Size", row.get("size"), "Error", "Size is missing.")

    # 9. Quantity Check
    qty_raw = row.get("quantity")
    if is_empty(qty_raw):
        add_exc("Quantity", qty_raw, "Error", "Quantity is missing.")
    else:
        try:
            qty = float(qty_raw)
            if qty < 0:
                add_exc("Quantity", qty_raw, "Error", "Quantity cannot be negative.")
            elif not qty.is_integer():
                add_exc("Quantity", qty_raw, "Error", "Quantity must be a whole integer.")
        except (ValueError, TypeError):
            add_exc("Quantity", qty_raw, "Error", "Quantity is not a valid number.")

    # 10. Price Check
    price_raw = row.get("price")
    if is_empty(price_raw):
        add_exc("Price", price_raw, "Error", "Price is missing.")
    else:
        try:
            price = float(price_raw)
            if price <= 0:
                add_exc("Price", price_raw, "Error", "Price must be greater than zero.")
        except (ValueError, TypeError):
            add_exc("Price", price_raw, "Error", "Price is not a valid number.")

    # ── Reference File Cross-Validation Logic ─────────────────────────────────

    # A. Content File checks
    if sku_to_article is not None:
        if sku_val:
            if sku_val in sku_to_article:
                ref_art = sku_to_article[sku_val]
                if norm_art and norm_art != ref_art:
                    add_exc("Article Number", art_num, "Error", f"Article mismatch: Uploaded Article No '{art_num}' does not match Content File Article No '{ref_art}' for SKU '{sku_val}'.")
                
                # Size Checkup: Refer UK size from Content File
                if size and sku_to_uksize and sku_val in sku_to_uksize:
                    ref_uksize = sku_to_uksize[sku_val]
                    if size.strip().lower() != ref_uksize.strip().lower():
                        add_exc("Size", size, "Error", f"Size mismatch: Uploaded size '{size}' does not match UK size '{ref_uksize}' in Content File for SKU '{sku_val}'.")
                
                # Gender Check from Content File
                if gender and sku_to_gender and sku_val in sku_to_gender:
                    ref_gender = sku_to_gender[sku_val]
                    if ref_gender and gender.strip().lower() != ref_gender.strip().lower():
                        add_exc("Gender", gender, "Warning", f"Gender mismatch: Uploaded gender '{gender}' does not match Content File gender '{ref_gender}' for SKU '{sku_val}'.")
            else:
                add_exc("SKU", sku_val, "Warning", f"SKU '{sku_val}' not found in Content File EAN lookup.")
                # Fallback size checking using Article No
                if norm_art and size and article_to_uksizes and norm_art in article_to_uksizes:
                    valid_uksizes = article_to_uksizes[norm_art]
                    if size.strip().lower() not in valid_uksizes:
                        add_exc("Size", size, "Error", f"Size mismatch: Uploaded size '{size}' is not in the list of valid UK sizes ({', '.join(sorted(list(valid_uksizes)))}) in Content File for Article No '{art_num}'.")
        else:
            # Check size by Article No alone if SKU is missing
            if norm_art and size and article_to_uksizes and norm_art in article_to_uksizes:
                valid_uksizes = article_to_uksizes[norm_art]
                if size.strip().lower() not in valid_uksizes:
                    add_exc("Size", size, "Error", f"Size mismatch: Uploaded size '{size}' is not in the list of valid UK sizes ({', '.join(sorted(list(valid_uksizes)))}) in Content File for Article No '{art_num}'.")

    # B. zEcom File checks
    if article_to_ecomstatus is not None:
        if norm_art:
            if norm_art in article_to_ecomstatus:
                ref_ecom_status = article_to_ecomstatus[norm_art]
                norm_up_status = _normalise_status(ecom_status)
                if norm_up_status != ref_ecom_status:
                    add_exc("E-commerce Status", ecom_status, "Error", f"Status mismatch: Uploaded status is '{ecom_status}' but zEcom File defines it as '{ref_ecom_status}' for Article No '{art_num}'.")
                
                # Launch Date Match
                if parsed_date and norm_art in article_to_launchdate:
                    ref_ld_str = article_to_launchdate[norm_art]
                    if ref_ld_str:
                        try:
                            ref_ld = pd.to_datetime(ref_ld_str).date()
                            if isinstance(parsed_date, datetime.datetime):
                                parsed_date = parsed_date.date()
                            if parsed_date != ref_ld:
                                add_exc("Launch Date", launch_date_raw, "Warning", f"Launch Date mismatch: Uploaded '{launch_date_raw}' does not match zEcom File Launch Date '{ref_ld_str}'.")
                        except Exception:
                            pass
            else:
                add_exc("Article Number", art_num, "Error", f"Article No '{art_num}' not found in zEcom File lookup.")

    return exceptions


def validate_row_post(
    row: pd.Series, 
    idx: int, 
    content_maps: Tuple = (None, None, None, None),
    zecom_maps: Tuple = (None, None),
    check_live_images: bool = False, 
    allowed_genders: List[str] = ALLOWED_GENDERS, 
    allowed_statuses: List[str] = ALLOWED_STATUSES
) -> List[Dict]:
    """
    Validates a single row for Post QC.
    Inherits Internal QC checks, then checks Images and Size Chart columns.
    """
    exceptions = validate_row_internal(row, idx, content_maps, zecom_maps, allowed_genders, allowed_statuses)
    
    source_file = row.get("_source_file", "Unknown File")
    row_num = row.get("_original_row_number", idx + 2)
    art_num = clean_str(row.get("article_number", ""))
    prod_name = clean_str(row.get("product_name", ""))
    gender = clean_str(row.get("gender", ""))

    def add_exc(field: str, val, severity: str, msg: str):
        exceptions.append({
            "Source File": source_file,
            "Row Number": row_num,
            "Article Number": art_num if art_num else "MISSING",
            "Product Name": prod_name if prod_name else "MISSING",
            "Field": field,
            "Value": str(val) if not pd.isna(val) else "MISSING",
            "Severity": severity,
            "Message": msg
        })

    # 1. Images
    images_raw = row.get("images")
    if is_empty(images_raw):
        add_exc("Images", images_raw, "Error", "Images column is missing or empty.")
    else:
        img_urls = [url.strip() for url in re.split(r'[,;\n]+', str(images_raw)) if url.strip()]
        if not img_urls:
            add_exc("Images", images_raw, "Error", "No valid image links found.")
        else:
            for i, url in enumerate(img_urls):
                if not URL_REGEX.match(url):
                    add_exc("Images", url, "Error", f"Image #{i+1} is not a valid URL format.")
                elif check_live_images:
                    try:
                        resp = requests.head(url, timeout=3)
                        if resp.status_code >= 400:
                            resp_get = requests.get(url, timeout=3, stream=True)
                            if resp_get.status_code >= 400:
                                add_exc("Images", url, "Error", f"Image #{i+1} link is broken (HTTP Status {resp_get.status_code}).")
                    except Exception as e:
                        add_exc("Images", url, "Error", f"Image #{i+1} link is unreachable: {type(e).__name__}")

    # 2. Size Chart
    size_chart_raw = row.get("size_chart")
    if is_empty(size_chart_raw):
        add_exc("Size Chart", size_chart_raw, "Error", "Size Chart attachment is missing.")
    else:
        size_chart = str(size_chart_raw).strip()
        if "http" in size_chart.lower() and not URL_REGEX.match(size_chart):
            add_exc("Size Chart", size_chart, "Warning", "Size Chart link is invalid URL format.")
        
        if not is_empty(gender):
            sc_low = size_chart.lower()
            g_low = gender.lower()
            if g_low in ["men", "boys"] and any(w in sc_low for w in ["women", "womens", "girl", "girls", "lady"]):
                add_exc("Size Chart", size_chart, "Warning", f"Size Chart reference seems to belong to females ('{size_chart}') but product gender is '{gender}'.")
            elif g_low in ["women", "girls"]:
                has_men_only = re.search(r"\bmen\b|\bmens\b|\bboy\b|\bboys\b", sc_low)
                if has_men_only:
                    add_exc("Size Chart", size_chart, "Warning", f"Size Chart reference seems to belong to males ('{size_chart}') but product gender is '{gender}'.")

    return exceptions


def validate_dataframe(
    df: pd.DataFrame, 
    qc_stage: str = "Internal QC",
    channel: str = "Lazada PH",
    content_df: pd.DataFrame = None,
    zecom_df: pd.DataFrame = None,
    check_live_images: bool = False, 
    allowed_genders: List[str] = ALLOWED_GENDERS, 
    allowed_statuses: List[str] = ALLOWED_STATUSES
) -> Tuple[pd.DataFrame, pd.DataFrame, List[str]]:
    """
    Validates a whole standardized DataFrame.
    """
    logs = []
    logs.append(f"Starting validation run at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logs.append(f"Validation Stage: {qc_stage} | Target Channel: {channel}")
    logs.append(f"Dataset contains {len(df)} records.")
    
    # Build maps
    with st.spinner("Indexing Content Reference mappings..."):
        content_maps = build_content_maps(content_df)
        logs.append("Content File mappings built successfully.")
    with st.spinner("Indexing zEcom Reference mappings..."):
        zecom_maps = build_zecom_maps(zecom_df, channel)
        logs.append(f"zEcom File mappings built successfully for channel: {channel}.")
        
    all_exceptions = []
    
    errors_col = []
    warnings_col = []
    status_col = []
    details_col = []
    
    # Group by SKU to check duplicate listings (Upload Sheet could have duplicates)
    # Using Article+Size composite key if SKU is missing
    duplicate_mask = df.duplicated(subset=["sku", "size"], keep=False)
    valid_skus = df["sku"].dropna().astype(str).str.strip()
    valid_skus = valid_skus[valid_skus != ""]
    
    duplicate_skus_sizes = set()
    dup_df = df[df["sku"].isin(valid_skus)]
    if not dup_df.empty:
        dups = dup_df[dup_df.duplicated(subset=["sku", "size"], keep=False)]
        for _, dup_row in dups.iterrows():
            sk = str(dup_row["sku"]).strip()
            sz = str(dup_row["size"]).strip()
            duplicate_skus_sizes.add((sk, sz))
            
    logs.append(f"Found {len(duplicate_skus_sizes)} duplicate sku+size combinations in upload sheet.")

    for idx, row in df.iterrows():
        if qc_stage == "Internal QC":
            row_exceptions = validate_row_internal(row, idx, content_maps, zecom_maps, allowed_genders, allowed_statuses)
        else:
            row_exceptions = validate_row_post(row, idx, content_maps, zecom_maps, check_live_images, allowed_genders, allowed_statuses)
            
        sk = _clean_sku(row.get("sku", ""))
        sz = clean_str(row.get("size", ""))
        if (sk, sz) in duplicate_skus_sizes:
            row_exceptions.append({
                "Source File": row.get("_source_file", "Unknown File"),
                "Row Number": row.get("_original_row_number", idx + 2),
                "Article Number": clean_str(row.get("article_number", "")),
                "Product Name": clean_str(row.get("product_name", "")),
                "Field": "SKU & Size",
                "Value": f"SKU: {sk}, Size: {sz}",
                "Severity": "Warning",
                "Message": f"Duplicate record: product with SKU '{sk}' and size '{sz}' is uploaded multiple times."
            })
            
        row_errors = sum(1 for e in row_exceptions if e["Severity"] == "Error")
        row_warnings = sum(1 for e in row_exceptions if e["Severity"] == "Warning")
        
        errors_col.append(row_errors)
        warnings_col.append(row_warnings)
        
        if row_errors > 0:
            status_col.append("Failed")
        elif row_warnings > 0:
            status_col.append("Warning")
        else:
            status_col.append("Passed")
            
        details_col.append("; ".join([f"{e['Field']}: {e['Message']}" for e in row_exceptions]))
        all_exceptions.extend(row_exceptions)
        
    val_df = df.copy()
    val_df["_qc_status"] = status_col
    val_df["_qc_errors"] = errors_col
    val_df["_qc_warnings"] = warnings_col
    val_df["_qc_details"] = details_col
    
    if all_exceptions:
        exc_df = pd.DataFrame(all_exceptions)
    else:
        exc_df = pd.DataFrame(columns=["Source File", "Row Number", "Article Number", "Product Name", "Field", "Value", "Severity", "Message"])
        
    logs.append(f"Validation completed. Passed: {status_col.count('Passed')}, Warnings: {status_col.count('Warning')}, Failed: {status_col.count('Failed')}")
    
    return exc_df, val_df, logs


def compare_source_and_live(source_df: pd.DataFrame, live_df: pd.DataFrame, match_column: str = "sku") -> Tuple[pd.DataFrame, Dict]:
    """
    Compares Standardized Source Data against Standardized Live Data.
    Normally matches by SKU.
    """
    comparison_records = []
    
    src_clean = source_df.copy()
    src_clean[match_column] = src_clean[match_column].astype(str).str.strip().apply(_clean_sku)
    src_clean = src_clean[src_clean[match_column] != ""]
    
    live_clean = live_df.copy()
    live_clean[match_column] = live_clean[match_column].astype(str).str.strip().apply(_clean_sku)
    live_clean = live_clean[live_clean[match_column] != ""]
    
    composite_match = "size" in src_clean.columns and "size" in live_clean.columns
    
    if composite_match:
        src_clean["_match_key"] = src_clean[match_column] + " | " + src_clean["size"].astype(str).str.strip()
        live_clean["_match_key"] = live_clean[match_column] + " | " + live_clean["size"].astype(str).str.strip()
        key_col = "_match_key"
    else:
        key_col = match_column
        
    src_grouped = src_clean.set_index(key_col)
    live_grouped = live_clean.set_index(key_col)
    
    all_keys = set(src_grouped.index).union(set(live_grouped.index))
    
    matched_count = 0
    mismatch_count = 0
    missing_in_live = 0
    missing_in_source = 0
    
    fields_to_compare = ["price", "quantity", "ecommerce_status", "product_name", "images", "size_chart"]
    
    for key in all_keys:
        in_source = key in src_grouped.index
        in_live = key in live_grouped.index
        
        if in_source and in_live:
            matched_count += 1
            src_row = src_grouped.loc[key]
            live_row = live_grouped.loc[key]
            
            if isinstance(src_row, pd.DataFrame):
                src_row = src_row.iloc[0]
            if isinstance(live_row, pd.DataFrame):
                live_row = live_row.iloc[0]
                
            art_num = src_row.get("article_number", "")
            sz = src_row.get("size", "N/A")
            prod_name = src_row.get("product_name", "")
            
            row_mismatches = []
            
            for field in fields_to_compare:
                # In standard live df loaded via loaders, columns are renamed to match standard comparison keys:
                # MP Stock -> quantity
                # MP Status -> ecommerce_status
                # MP Price -> price
                # MP Product Name -> product_name
                # Let's map target comparison keys
                src_field = field
                live_field = field
                
                # Check for marketplace specific columns from live_loaders
                if field == "quantity" and "MP Stock" in live_row:
                    live_field = "MP Stock"
                if field == "ecommerce_status" and "MP Status" in live_row:
                    live_field = "MP Status"
                if field == "price" and "MP Price" in live_row:
                    live_field = "MP Price"
                if field == "product_name" and "MP Product Name" in live_row:
                    live_field = "MP Product Name"

                if src_field in src_row and live_field in live_row:
                    s_val = src_row[src_field]
                    l_val = live_row[live_field]
                    
                    is_diff = False
                    if field in ["price", "quantity"]:
                        try:
                            # Strip currency or symbols
                            s_f = float(re.sub(r'[^\d\.]', '', str(s_val))) if s_val else 0.0
                            l_f = float(re.sub(r'[^\d\.]', '', str(l_val))) if l_val else 0.0
                            is_diff = not np.isclose(s_f, l_f)
                        except (ValueError, TypeError):
                            is_diff = str(s_val).strip().lower() != str(l_val).strip().lower()
                    else:
                        is_diff = _normalise_status(s_val) != _normalise_status(l_val) if field == "ecommerce_status" else clean_str(s_val).lower() != clean_str(l_val).lower()
                        
                    if is_diff:
                        row_mismatches.append(field)
                        comparison_records.append({
                            "Article Number": art_num,
                            "Size": sz,
                            "Product Name": prod_name,
                            "Comparison Field": field.replace("_", " ").title(),
                            "Source Value": str(s_val),
                            "Live Value": str(l_val),
                            "Match Status": "Mismatch",
                            "Description": f"Discrepancy in {field.replace('_', ' ')}. Upload Sheet: {s_val}, Live Store: {l_val}"
                        })
            
            if row_mismatches:
                mismatch_count += 1
            else:
                comparison_records.append({
                    "Article Number": art_num,
                    "Size": sz,
                    "Product Name": prod_name,
                    "Comparison Field": "All Fields",
                    "Source Value": "-",
                    "Live Value": "-",
                    "Match Status": "Passed",
                    "Description": "All compared listing attributes match correctly."
                })
                
        elif in_source:
            missing_in_live += 1
            src_row = src_grouped.loc[key]
            if isinstance(src_row, pd.DataFrame):
                src_row = src_row.iloc[0]
                
            comparison_records.append({
                "Article Number": src_row.get("article_number", ""),
                "Size": src_row.get("size", "N/A"),
                "Product Name": src_row.get("product_name", ""),
                "Comparison Field": "Listing Presence",
                "Source Value": "Present",
                "Live Value": "Missing",
                "Match Status": "Failed (Missing Live)",
                "Description": "Product exists in uploaded sheet but is missing from live store listings."
            })
        else:
            missing_in_source += 1
            live_row = live_grouped.loc[key]
            if isinstance(live_row, pd.DataFrame):
                live_row = live_row.iloc[0]
                
            # If live row has SKU, try to lookup Article No from content?
            comparison_records.append({
                "Article Number": live_row.get("Article No", "Unknown"),
                "Size": live_row.get("size", "N/A") if "size" in live_row else "N/A",
                "Product Name": live_row.get("product_name", "Unknown"),
                "Comparison Field": "Listing Presence",
                "Source Value": "Missing",
                "Live Value": "Present",
                "Match Status": "Warning (Extra Live)",
                "Description": "Product is live on store but missing from uploaded master sheet."
            })
            
    summary_metrics = {
        "Total SKU variants Analyzed": len(all_keys),
        "Fully Matched Items": matched_count - mismatch_count,
        "Items with Mismatches": mismatch_count,
        "Missing in Live Store": missing_in_live,
        "Extra Live Store Listings": missing_in_source
    }
    
    if comparison_records:
        comp_df = pd.DataFrame(comparison_records)
    else:
        comp_df = pd.DataFrame(columns=["Article Number", "Size", "Product Name", "Comparison Field", "Source Value", "Live Value", "Match Status", "Description"])
        
    return comp_df, summary_metrics

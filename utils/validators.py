import re
import datetime
import pandas as pd
import numpy as np
import requests
from typing import Dict, List, Tuple

# Default allowed values
ALLOWED_GENDERS = ["men", "women", "unisex", "kids", "boys", "girls"]
ALLOWED_STATUSES = ["active", "inactive", "draft", "delisted", "suspended", "live", "on", "off"]

# Regular expressions for validation
URL_REGEX = re.compile(
    r'^(?:http|ftp)s?://' # http:// or https://
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' # domain...
    r'localhost|' # localhost...
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
    r'(?::\d+)?' # optional port
    r'(?:/?|[/?]\S+)$', re.IGNORECASE)

def is_empty(val) -> bool:
    """Helper to check if a value is null, NaN, or whitespace."""
    if pd.isna(val) or val is None:
        return True
    val_str = str(val).strip()
    return val_str == "" or val_str.lower() in ["nan", "null", "<na>", "none"]

def clean_str(val) -> str:
    """Helper to clean string values."""
    if is_empty(val):
        return ""
    return str(val).strip()

def validate_row_internal(row: pd.Series, idx: int, allowed_genders: List[str] = ALLOWED_GENDERS, allowed_statuses: List[str] = ALLOWED_STATUSES) -> List[Dict]:
    """
    Validates a single row for Internal QC.
    Returns a list of exception dicts: {row_num, article_num, field, value, severity, message}
    """
    exceptions = []
    source_file = row.get("_source_file", "Unknown File")
    row_num = row.get("_original_row_number", idx + 2)
    art_num = clean_str(row.get("article_number", ""))
    prod_name = clean_str(row.get("product_name", ""))
    
    # Helper to add exceptions
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

    # 1. Article Number
    if is_empty(row.get("article_number")):
        add_exc("Article Number", row.get("article_number"), "Error", "Article Number is missing.")
    else:
        # Check alphanumeric characters
        if not re.match(r"^[a-zA-Z0-9-_]+$", art_num):
            add_exc("Article Number", art_num, "Warning", "Article Number contains special characters. Standard alphanumeric format recommended.")

    # 2. E-commerce Status
    ecom_status = clean_str(row.get("ecommerce_status"))
    if is_empty(row.get("ecommerce_status")):
        add_exc("E-commerce Status", row.get("ecommerce_status"), "Error", "E-commerce Status is missing.")
    elif ecom_status.lower() not in [s.lower() for s in allowed_statuses]:
        add_exc("E-commerce Status", ecom_status, "Warning", f"Status '{ecom_status}' is not in standard list ({', '.join(allowed_statuses)}).")

    # 3. Launch Date
    launch_date_raw = row.get("launch_date")
    if is_empty(launch_date_raw):
        add_exc("Launch Date", launch_date_raw, "Error", "Launch Date is missing.")
    else:
        # Check date parsing
        parsed_date = None
        if isinstance(launch_date_raw, (datetime.datetime, datetime.date)):
            parsed_date = launch_date_raw
        else:
            # Try to parse string
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d", "%d-%m-%Y"):
                try:
                    parsed_date = datetime.datetime.strptime(str(launch_date_raw).strip(), fmt).date()
                    break
                except ValueError:
                    continue
            
            # Try general pandas parsing if formatting trial failed
            if parsed_date is None:
                try:
                    parsed_date = pd.to_datetime(launch_date_raw).date()
                except Exception:
                    pass
                    
        if parsed_date is None:
            add_exc("Launch Date", launch_date_raw, "Error", "Launch Date has an invalid format. Recommended: YYYY-MM-DD.")
        else:
            # Check if launch date is in past (Warning) or future
            today = datetime.date.today()
            if isinstance(parsed_date, datetime.datetime):
                parsed_date = parsed_date.date()
                
            if parsed_date < today - datetime.timedelta(days=365*5):
                add_exc("Launch Date", launch_date_raw, "Warning", f"Launch Date is far in the past ({parsed_date}). Please verify.")
            elif parsed_date > today + datetime.timedelta(days=365):
                add_exc("Launch Date", launch_date_raw, "Warning", f"Launch Date is far in the future ({parsed_date}). Please verify.")

    # 4. Gender
    gender = clean_str(row.get("gender"))
    if is_empty(row.get("gender")):
        add_exc("Gender", row.get("gender"), "Error", "Gender is missing.")
    elif gender.lower() not in [g.lower() for g in allowed_genders]:
        add_exc("Gender", gender, "Error", f"Gender '{gender}' is invalid. Allowed: {', '.join(allowed_genders)}.")

    # 5. Product Name & Gender Mismatch
    if is_empty(row.get("product_name")):
        add_exc("Product Name", row.get("product_name"), "Error", "Product Name is missing.")
    elif not is_empty(row.get("gender")) and gender.lower() in [g.lower() for g in allowed_genders]:
        gender_low = gender.lower()
        prod_name_low = prod_name.lower()
        
        # Word boundaries match to avoid false positive in words (e.g. matching "men" in "women")
        male_mismatch_keywords = [
            r"\bwomen\b", r"\bwomens\b", r"\bgirl\b", r"\bgirls\b", r"\blady\b", 
            r"\bladies\b", r"\bshe\b", r"\bher\b", r"\bfemale\b", r"\bwoman\b"
        ]
        female_mismatch_keywords = [
            r"\bmen\b", r"\bmens\b", r"\bboy\b", r"\bboys\b", r"\bhim\b", r"\bhis\b", r"\bmale\b"
        ]
        
        # If Gender is Male-centric (Men, Boys)
        if gender_low in ["men", "boys"]:
            mismatch_found = False
            for pattern in male_mismatch_keywords:
                if re.search(pattern, prod_name_low):
                    add_exc("Product Name", prod_name, "Error", f"Gender mismatch: Product Name contains female keyword '{re.sub(r'[^a-zA-Z]', '', pattern)}' but Gender is '{gender}'.")
                    mismatch_found = True
                    break
        # If Gender is Female-centric (Women, Girls)
        elif gender_low in ["women", "girls"]:
            mismatch_found = False
            for pattern in female_mismatch_keywords:
                # Need to be careful because \bmen\b could match in womens? No, word boundaries protect us.
                if re.search(pattern, prod_name_low):
                    add_exc("Product Name", prod_name, "Error", f"Gender mismatch: Product Name contains male keyword '{re.sub(r'[^a-zA-Z]', '', pattern)}' but Gender is '{gender}'.")
                    mismatch_found = True
                    break

    # 6. Color Name
    if is_empty(row.get("color_name")):
        add_exc("Color Name", row.get("color_name"), "Error", "Color Name is missing.")

    # 7. Size
    if is_empty(row.get("size")):
        add_exc("Size", row.get("size"), "Error", "Size is missing.")

    # 8. Quantity
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

    # 9. Price
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

    return exceptions


def validate_row_post(row: pd.Series, idx: int, check_live_images: bool = False, allowed_genders: List[str] = ALLOWED_GENDERS, allowed_statuses: List[str] = ALLOWED_STATUSES) -> List[Dict]:
    """
    Validates a single row for Post QC.
    Inherits Internal QC checks, then checks Images and Size Chart columns.
    """
    exceptions = validate_row_internal(row, idx, allowed_genders, allowed_statuses)
    
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
        # Split images by comma/semicolon/newline
        img_urls = [url.strip() for url in re.split(r'[,;\n]+', str(images_raw)) if url.strip()]
        
        if not img_urls:
            add_exc("Images", images_raw, "Error", "No valid image links found.")
        else:
            # Check format of each URL
            for i, url in enumerate(img_urls):
                if not URL_REGEX.match(url):
                    add_exc("Images", url, "Error", f"Image #{i+1} is not a valid URL format.")
                elif check_live_images:
                    # Optional live HTTP validation
                    try:
                        resp = requests.head(url, timeout=3)
                        if resp.status_code >= 400:
                            # Try GET in case HEAD is blocked
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
        # Basic check for URL or file reference
        if "http" in size_chart.lower() and not URL_REGEX.match(size_chart):
            add_exc("Size Chart", size_chart, "Warning", "Size Chart link is invalid URL format.")
        
        # Gender mismatch check on Size Chart name if applicable
        if not is_empty(gender):
            sc_low = size_chart.lower()
            g_low = gender.lower()
            
            if g_low in ["men", "boys"] and any(w in sc_low for w in ["women", "womens", "girl", "girls", "lady"]):
                add_exc("Size Chart", size_chart, "Warning", f"Size Chart reference seems to belong to females ('{size_chart}') but product gender is '{gender}'.")
            elif g_low in ["women", "girls"] and any(w in sc_low for w in ["men", "mens", "boy", "boys"]):
                # Ensure we don't flag "women" containing "men"
                # A simple check: if "men" is in sc_low but "women" is NOT, or check word boundaries
                has_men_only = re.search(r"\bmen\b|\bmens\b|\bboy\b|\bboys\b", sc_low)
                if has_men_only:
                    add_exc("Size Chart", size_chart, "Warning", f"Size Chart reference seems to belong to males ('{size_chart}') but product gender is '{gender}'.")

    return exceptions


def validate_dataframe(df: pd.DataFrame, qc_stage: str = "Internal QC", check_live_images: bool = False, allowed_genders: List[str] = ALLOWED_GENDERS, allowed_statuses: List[str] = ALLOWED_STATUSES) -> Tuple[pd.DataFrame, pd.DataFrame, List[str]]:
    """
    Validates a whole standardized DataFrame.
    Returns:
      1. Aggregated exceptions DataFrame
      2. Validated DataFrame with extra status columns (_qc_status, _qc_errors, _qc_warnings, _qc_details)
      3. Validation log lines
    """
    logs = []
    logs.append(f"Starting validation run at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logs.append(f"Validation Stage: {qc_stage}")
    logs.append(f"Dataset contains {len(df)} records.")
    
    all_exceptions = []
    
    # Track stats
    errors_col = []
    warnings_col = []
    status_col = []
    details_col = []
    
    # Group by article number to find duplicate listings in the upload
    duplicate_mask = df.duplicated(subset=["article_number", "size"], keep=False)
    # Filter out empty SKU rows when calculating duplicates to prevent false duplicate errors on blank cells
    valid_art_nums = df["article_number"].dropna().astype(str).str.strip()
    valid_art_nums = valid_art_nums[valid_art_nums != ""]
    
    duplicate_articles_sizes = set()
    dup_df = df[df["article_number"].isin(valid_art_nums)]
    if not dup_df.empty:
        # Group by article and size
        dups = dup_df[dup_df.duplicated(subset=["article_number", "size"], keep=False)]
        for _, dup_row in dups.iterrows():
            art = str(dup_row["article_number"]).strip()
            sz = str(dup_row["size"]).strip()
            duplicate_articles_sizes.add((art, sz))
            
    logs.append(f"Found {len(duplicate_articles_sizes)} duplicate article+size combinations.")

    for idx, row in df.iterrows():
        # Standard row validations
        if qc_stage == "Internal QC":
            row_exceptions = validate_row_internal(row, idx, allowed_genders, allowed_statuses)
        else:
            row_exceptions = validate_row_post(row, idx, check_live_images, allowed_genders, allowed_statuses)
            
        # Add duplicate warning
        art = clean_str(row.get("article_number", ""))
        sz = clean_str(row.get("size", ""))
        if (art, sz) in duplicate_articles_sizes:
            row_exceptions.append({
                "Source File": row.get("_source_file", "Unknown File"),
                "Row Number": row.get("_original_row_number", idx + 2),
                "Article Number": art if art else "MISSING",
                "Product Name": clean_str(row.get("product_name", "")),
                "Field": "Article Number & Size",
                "Value": f"Article: {art}, Size: {sz}",
                "Severity": "Warning",
                "Message": f"Duplicate record: product with article number '{art}' and size '{sz}' is listed multiple times in the dataset."
            })
            
        # Tally counts
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
        
    # Build updated DataFrame
    val_df = df.copy()
    val_df["_qc_status"] = status_col
    val_df["_qc_errors"] = errors_col
    val_df["_qc_warnings"] = warnings_col
    val_df["_qc_details"] = details_col
    
    # Convert exceptions list to DataFrame
    if all_exceptions:
        exc_df = pd.DataFrame(all_exceptions)
    else:
        exc_df = pd.DataFrame(columns=["Source File", "Row Number", "Article Number", "Product Name", "Field", "Value", "Severity", "Message"])
        
    logs.append(f"Validation completed. Passed: {status_col.count('Passed')}, Warnings: {status_col.count('Warning')}, Failed: {status_col.count('Failed')}")
    
    return exc_df, val_df, logs


def compare_source_and_live(source_df: pd.DataFrame, live_df: pd.DataFrame, match_column: str = "article_number") -> Tuple[pd.DataFrame, Dict]:
    """
    Compares Standardized Source Data against Standardized Live Data.
    Performs verification comparisons across overlapping fields:
      - Price
      - Quantity (Stock)
      - E-commerce Status
      - Product Name
      - Images
      - Size Chart
    Returns:
      1. Comparison details DataFrame
      2. High level metrics dictionary
    """
    comparison_records = []
    
    # Index by matching key
    # Ensure keys are strings, clean and non-empty
    src_clean = source_df.copy()
    src_clean[match_column] = src_clean[match_column].astype(str).str.strip()
    src_clean = src_clean[src_clean[match_column] != ""]
    
    live_clean = live_df.copy()
    live_clean[match_column] = live_clean[match_column].astype(str).str.strip()
    live_clean = live_clean[live_clean[match_column] != ""]
    
    # We want to match on Article+Size if size matches, otherwise match by Article.
    # Since products have size-level variants (prices & quantities differ per size),
    # matching by Article + Size is the most precise.
    # Let's check if 'size' is in both, if so, match by composite key (Article + Size).
    composite_match = "size" in src_clean.columns and "size" in live_clean.columns
    
    if composite_match:
        src_clean["_match_key"] = src_clean[match_column] + " | " + src_clean["size"].astype(str).str.strip()
        live_clean["_match_key"] = live_clean[match_column] + " | " + live_clean["size"].astype(str).str.strip()
        key_col = "_match_key"
    else:
        key_col = match_column
        
    # Group source and live by key
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
        
        # Display key representation for Excel Row
        display_key = key
        
        if in_source and in_live:
            matched_count += 1
            src_row = src_grouped.loc[key]
            live_row = live_grouped.loc[key]
            
            # If there are duplicates in indices, take the first one or iterate. 
            # In pandas loc could return Series or DataFrame. Handle Series.
            if isinstance(src_row, pd.DataFrame):
                src_row = src_row.iloc[0]
            if isinstance(live_row, pd.DataFrame):
                live_row = live_row.iloc[0]
                
            art_num = src_row.get("article_number", "")
            sz = src_row.get("size", "N/A")
            prod_name = src_row.get("product_name", "")
            
            row_mismatches = []
            
            for field in fields_to_compare:
                if field in src_row and field in live_row:
                    s_val = src_row[field]
                    l_val = live_row[field]
                    
                    # Normalize comparison based on type
                    is_diff = False
                    
                    if field in ["price", "quantity"]:
                        try:
                            is_diff = not np.isclose(float(s_val), float(l_val))
                        except (ValueError, TypeError):
                            is_diff = str(s_val).strip().lower() != str(l_val).strip().lower()
                    else:
                        is_diff = clean_str(s_val).lower() != clean_str(l_val).lower()
                        
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
                            "Description": f"Discrepancy in {field.replace('_', ' ')}. Source: {s_val}, Live: {l_val}"
                        })
            
            if row_mismatches:
                mismatch_count += 1
            else:
                # Add a passed row to keep track
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
                "Description": "Product exists in source sheet but is missing from live listings."
            })
        else:
            missing_in_source += 1
            live_row = live_grouped.loc[key]
            if isinstance(live_row, pd.DataFrame):
                live_row = live_row.iloc[0]
                
            comparison_records.append({
                "Article Number": live_row.get("article_number", ""),
                "Size": live_row.get("size", "N/A"),
                "Product Name": live_row.get("product_name", ""),
                "Comparison Field": "Listing Presence",
                "Source Value": "Missing",
                "Live Value": "Present",
                "Match Status": "Warning (Extra Live)",
                "Description": "Product is live on store but missing from master source list."
            })
            
    summary_metrics = {
        "Total Keys Analyzed": len(all_keys),
        "Fully Matched Items": matched_count - mismatch_count,
        "Items with Mismatches": mismatch_count,
        "Missing in Live Listings": missing_in_live,
        "Extra Live Listings": missing_in_source
    }
    
    if comparison_records:
        comp_df = pd.DataFrame(comparison_records)
    else:
        comp_df = pd.DataFrame(columns=["Article Number", "Size", "Product Name", "Comparison Field", "Source Value", "Live Value", "Match Status", "Description"])
        
    return comp_df, summary_metrics

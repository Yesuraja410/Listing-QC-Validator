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

# Size Correction Dictionary
SIZE_CORRECTIONS = {
    "youth": "M",
    "adult": "L",
    "small": "S",
    "osfa": "One Size",
    "2xl": "XXL",
    "3xl": "XXXL",
    "4xl": "XXXXL",
    "5xl": "XXXXXL",
    "6xl": "XXXXXXL",
    "7xl": "XXXXXXXL"
}

# Common Malay e-commerce keywords for TikTok MY validations
MALAY_KEYWORDS = [
    r"\buntuk\b", r"\bdengan\b", r"\byang\b", r"\bpada\b", r"\badalah\b", r"\bdan\b",
    r"\blelaki\b", r"\bperempuan\b", r"\bwanita\b", r"\bsukan\b", r"\bkasut\b", r"\bbaju\b",
    r"\bseluar\b", r"\bkanak\b", r"\bbudak\b", r"\basli\b", r"\bmurah\b", r"\bsaiz\b",
    r"\bwarna\b", r"\bhitam\b", r"\bputih\b", r"\bmerah\b", r"\bbiru\b", r"\bhijau\b",
    r"\bkuning\b", r"\bberlari\b", r"\bjersey\b"
]

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

def correct_size(sz: str) -> str:
    """Applies size corrections (e.g. Youth -> M, 2XL -> XXL)."""
    s = str(sz).strip()
    s_low = s.lower()
    if s_low in SIZE_CORRECTIONS:
        return SIZE_CORRECTIONS[s_low]
    return s

def is_footwear(product_name: str) -> bool:
    """Classifies footwear products based on title keywords."""
    name_low = str(product_name).lower()
    footwear_kws = ["shoe", "shoes", "sneaker", "sneakers", "sandal", "sandals", "slide", "slides", "boot", "boots", "slippers", "cleat", "cleats", "footwear"]
    return any(kw in name_low for kw in footwear_kws)

def is_kids_apparel(gender: str, product_name: str) -> bool:
    """Classifies Kids Apparel (Zalora Rus size rule)."""
    g_low = str(gender).lower()
    is_kid = g_low in ["kids", "boys", "girls"]
    # Apparel is anything that is NOT footwear
    return is_kid and not is_footwear(product_name)

# ── Reference Mappings Builders ───────────────────────────────────────────────

def build_content_maps(content_df: pd.DataFrame) -> Tuple[Dict, Dict, Dict, Dict, Dict, Dict, Dict, Dict]:
    """
    Builds lookup tables from Content File for UK, US, and Russian size mappings.
    """
    sku_to_article = {}
    sku_to_uksize = {}
    sku_to_ussize = {}
    sku_to_russize = {}
    sku_to_gender = {}
    
    article_to_uksizes = {}
    article_to_ussizes = {}
    article_to_russizes = {}
    
    if content_df is not None and not content_df.empty:
        has_sku = "SKU" in content_df.columns
        has_art = "Article No" in content_df.columns
        has_uk = "uk_size" in content_df.columns
        has_us = "us_size" in content_df.columns
        has_rus = "rus_size" in content_df.columns
        gender_col = next((c for c in content_df.columns if c.lower() in ["gender", "sex"]), None)
        
        for _, r in content_df.iterrows():
            sku_val = _clean_sku(r.get("SKU")) if has_sku else ""
            art_val = _normalise_article_no(r.get("Article No")) if has_art else ""
            uk_val = _safe_str(r.get("uk_size")).strip() if has_uk else ""
            us_val = _safe_str(r.get("us_size")).strip() if has_us else ""
            rus_val = _safe_str(r.get("rus_size")).strip() if has_rus else ""
            
            if sku_val:
                if art_val:
                    sku_to_article[sku_val] = art_val
                if uk_val:
                    sku_to_uksize[sku_val] = uk_val
                if us_val:
                    sku_to_ussize[sku_val] = us_val
                if rus_val:
                    sku_to_russize[sku_val] = rus_val
                if gender_col:
                    sku_to_gender[sku_val] = _safe_str(r.get(gender_col)).strip()
                    
            if art_val:
                if art_val not in article_to_uksizes:
                    article_to_uksizes[art_val] = set()
                if art_val not in article_to_ussizes:
                    article_to_ussizes[art_val] = set()
                if art_val not in article_to_russizes:
                    article_to_russizes[art_val] = set()
                    
                if uk_val:
                    article_to_uksizes[art_val].add(uk_val.lower())
                if us_val:
                    article_to_ussizes[art_val].add(us_val.lower())
                if rus_val:
                    article_to_russizes[art_val].add(rus_val.lower())
                
    return (
        sku_to_article, sku_to_uksize, sku_to_ussize, sku_to_russize, sku_to_gender,
        article_to_uksizes, article_to_ussizes, article_to_russizes
    )


def build_zecom_maps(zecom_df: pd.DataFrame, channel: str) -> Tuple[Dict, Dict, Dict]:
    """
    Builds lookup tables from zEcom File:
    1. article_to_launchdate: Article No -> Launch Date
    2. article_to_ecomstatus: Article No -> Ecom Status (Active vs Inactive)
    3. article_to_rrpprice: Article No -> RRP Price
    """
    article_to_launchdate = {}
    article_to_ecomstatus = {}
    article_to_rrpprice = {}
    
    if zecom_df is not None and not zecom_df.empty:
        platform = channel.split()[0].lower()
        ecom_col = f"Ecom_{platform.capitalize()}"
        
        has_art = "Article No" in zecom_df.columns
        has_launch = "Launch Date" in zecom_df.columns
        has_ecom = ecom_col in zecom_df.columns
        has_rrp = "rrp_price" in zecom_df.columns
        
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
                    
                if has_rrp:
                    article_to_rrpprice[art_val] = _safe_str(r.get("rrp_price"))
                    
    return article_to_launchdate, article_to_ecomstatus, article_to_rrpprice

# ── Row Validation Logic ──────────────────────────────────────────────────────

def validate_row_internal(
    row: pd.Series, 
    idx: int, 
    channel: str,
    content_maps: Tuple = (None, None, None, None, None, None, None, None),
    zecom_maps: Tuple = (None, None, None),
    allowed_genders: List[str] = ALLOWED_GENDERS, 
    allowed_statuses: List[str] = ALLOWED_STATUSES
) -> List[Dict]:
    """
    Validates a single row for Internal QC with reference lookups, US/Rus size checks, and RRP price checks.
    """
    exceptions = []
    source_file = row.get("_source_file", "Unknown File")
    row_num = row.get("_original_row_number", idx + 2)
    art_num = clean_str(row.get("article_number", ""))
    norm_art = _normalise_article_no(art_num)
    sku_val = _clean_sku(row.get("sku", ""))
    prod_name = clean_str(row.get("product_name", ""))
    gender = clean_str(row.get("gender", ""))
    ecom_status = clean_str(row.get("ecommerce_status", ""))
    
    # ── 1. Apply Size Corrections ──
    raw_size = clean_str(row.get("size", ""))
    size = correct_size(raw_size)
    
    sku_to_article, sku_to_uksize, sku_to_ussize, sku_to_russize, sku_to_gender, \
        article_to_uksizes, article_to_ussizes, article_to_russizes = content_maps
        
    article_to_launchdate, article_to_ecomstatus, article_to_rrpprice = zecom_maps

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

    # 9. Strict Quantity Check: Quantity must be exactly 0
    qty_raw = row.get("quantity")
    if is_empty(qty_raw):
        add_exc("Quantity", qty_raw, "Error", "Quantity is missing.")
    else:
        try:
            qty = float(qty_raw)
            if qty != 0:
                add_exc("Quantity", qty_raw, "Error", f"Quantity must be exactly 0 (Uploaded: {qty_raw}).")
        except (ValueError, TypeError):
            add_exc("Quantity", qty_raw, "Error", "Quantity is not a valid number.")

    # 10. Price Check & RRP zEcom Comparison
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

    # ── TikTok MY Malay Language Validation ──
    if "TikTok" in channel:
        title_desc_combined = prod_name.lower()
        # Malay lang check: check if any of the common malay keywords are in title/name
        has_malay = any(re.search(pat, title_desc_combined) for pat in MALAY_KEYWORDS)
        if not has_malay:
            add_exc("Product Name", prod_name, "Warning", "TikTok Listing: Title/Description should contain Malay language words (e.g. untuk, lelaki, wanita, kasut, saiz).")

    # ── Reference File Cross-Validation Logic ─────────────────────────────────

    # A. Content File checks
    if sku_to_article is not None:
        if sku_val:
            if sku_val in sku_to_article:
                ref_art = sku_to_article[sku_val]
                if norm_art and norm_art != ref_art:
                    add_exc("Article Number", art_num, "Error", f"Article mismatch: Uploaded Article No '{art_num}' does not match Content File Article No '{ref_art}' for SKU '{sku_val}'.")
                
                # Size Checkup dynamic logic: US size / Rus size / UK size
                if size:
                    # Choose size reference based on Channel & Footwear / Apparel classification
                    if channel == "Lazada PH" and is_footwear(prod_name):
                        # US Size
                        ref_size = sku_to_ussize.get(sku_val, "")
                        size_type = "US size"
                        valid_sizes_for_art = article_to_ussizes.get(norm_art, set())
                    elif channel in ["Zalora SG", "Zalora MY", "Zalora PH"] and is_kids_apparel(gender, prod_name):
                        # Rus Size
                        ref_size = sku_to_russize.get(sku_val, "")
                        size_type = "Rus size"
                        valid_sizes_for_art = article_to_russizes.get(norm_art, set())
                    else:
                        # UK Size (Default)
                        ref_size = sku_to_uksize.get(sku_val, "")
                        size_type = "UK size"
                        valid_sizes_for_art = article_to_uksizes.get(norm_art, set())
                        
                    if ref_size:
                        if size.strip().lower() != ref_size.strip().lower():
                            add_exc("Size", raw_size, "Error", f"Size mismatch: Size '{raw_size}' (Normalized: '{size}') does not match reference {size_type} '{ref_size}' in Content File for SKU '{sku_val}'.")
                    else:
                        add_exc("Size", raw_size, "Warning", f"No {size_type} mapped in Content File for SKU '{sku_val}'.")
                
                # Gender Check from Content File
                if gender and sku_to_gender and sku_val in sku_to_gender:
                    ref_gender = sku_to_gender[sku_val]
                    if ref_gender and gender.strip().lower() != ref_gender.strip().lower():
                        add_exc("Gender", gender, "Warning", f"Gender mismatch: Uploaded gender '{gender}' does not match Content File gender '{ref_gender}' for SKU '{sku_val}'.")
            else:
                add_exc("SKU", sku_val, "Warning", f"SKU '{sku_val}' not found in Content File lookup.")
                # Fallback size checking using Article No
                if norm_art and size:
                    if channel == "Lazada PH" and is_footwear(prod_name):
                        valid_sizes = article_to_ussizes.get(norm_art, set())
                        size_type = "US size"
                    elif channel in ["Zalora SG", "Zalora MY", "Zalora PH"] and is_kids_apparel(gender, prod_name):
                        valid_sizes = article_to_russizes.get(norm_art, set())
                        size_type = "Rus size"
                    else:
                        valid_sizes = article_to_uksizes.get(norm_art, set())
                        size_type = "UK size"
                        
                    if valid_sizes and size.strip().lower() not in valid_sizes:
                        add_exc("Size", raw_size, "Error", f"Size mismatch: Size '{raw_size}' (Normalized: '{size}') is not in the list of valid {size_type}s ({', '.join(sorted(list(valid_sizes)))}) in Content File for Article No '{art_num}'.")
        else:
            # Check size by Article No alone if SKU is missing
            if norm_art and size:
                if channel == "Lazada PH" and is_footwear(prod_name):
                    valid_sizes = article_to_ussizes.get(norm_art, set())
                    size_type = "US size"
                elif channel in ["Zalora SG", "Zalora MY", "Zalora PH"] and is_kids_apparel(gender, prod_name):
                    valid_sizes = article_to_russizes.get(norm_art, set())
                    size_type = "Rus size"
                else:
                    valid_sizes = article_to_uksizes.get(norm_art, set())
                    size_type = "UK size"
                    
                if valid_sizes and size.strip().lower() not in valid_sizes:
                    add_exc("Size", raw_size, "Error", f"Size mismatch: Size '{raw_size}' (Normalized: '{size}') is not in the list of valid {size_type}s ({', '.join(sorted(list(valid_sizes)))}) in Content File for Article No '{art_num}'.")

    # B. zEcom File checks (including RRP price validations)
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
                            
                # zEcom RRP Price validation
                if price_raw and norm_art in article_to_rrpprice:
                    rrp_raw = article_to_rrpprice[norm_art]
                    if rrp_raw:
                        try:
                            uploaded_p = float(price_raw)
                            # Strip any currency characters in reference price
                            ref_p_f = float(re.sub(r'[^\d\.]', '', str(rrp_raw)))
                            if not np.isclose(uploaded_p, ref_p_f):
                                add_exc("Price", price_raw, "Error", f"Price mismatch: Uploaded price '{price_raw}' does not match RRP Price '{rrp_raw}' from zEcom File for Article No '{art_num}'.")
                        except Exception:
                            pass
            else:
                add_exc("Article Number", art_num, "Error", f"Article No '{art_num}' not found in zEcom File lookup.")

    return exceptions


def validate_row_post(
    row: pd.Series, 
    idx: int, 
    channel: str,
    content_maps: Tuple = (None, None, None, None, None, None, None, None),
    zecom_maps: Tuple = (None, None, None),
    check_live_images: bool = False, 
    allowed_genders: List[str] = ALLOWED_GENDERS, 
    allowed_statuses: List[str] = ALLOWED_STATUSES
) -> List[Dict]:
    """
    Validates a single row for Post QC.
    Inherits Internal QC checks, then checks Images and Size Chart columns.
    """
    exceptions = validate_row_internal(row, idx, channel, content_maps, zecom_maps, allowed_genders, allowed_statuses)
    
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
    Validates a whole standardized DataFrame with UK, US, Russian size and zEcom RRP rules.
    """
    logs = []
    logs.append(f"Starting validation run at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logs.append(f"Validation Stage: {qc_stage} | Target Channel: {channel}")
    logs.append(f"Dataset contains {len(df)} records.")
    
    content_maps = build_content_maps(content_df)
    logs.append("Content File size mappings built successfully.")
    zecom_maps = build_zecom_maps(zecom_df, channel)
    logs.append(f"zEcom File status and RRP price mappings built successfully.")
        
    all_exceptions = []
    
    errors_col = []
    warnings_col = []
    status_col = []
    details_col = []
    
    # Group by SKU and Size (after applying corrections) to find duplicates
    duplicate_skus_sizes = set()
    if "sku" in df.columns and "size" in df.columns:
        valid_skus = df["sku"].dropna().astype(str).str.strip()
        valid_skus = valid_skus[valid_skus != ""]
        dup_df = df[df["sku"].isin(valid_skus)].copy()
        if not dup_df.empty:
            dup_df["_corrected_size"] = dup_df["size"].apply(correct_size).astype(str).str.strip().str.lower()
            dups = dup_df[dup_df.duplicated(subset=["sku", "_corrected_size"], keep=False)]
            for _, dup_row in dups.iterrows():
                sk = str(dup_row["sku"]).strip()
                sz = str(dup_row["_corrected_size"]).strip()
                duplicate_skus_sizes.add((sk, sz))
                
    logs.append(f"Found {len(duplicate_skus_sizes)} duplicate sku+size combinations in upload sheet.")

    for idx, row in df.iterrows():
        if qc_stage == "Internal QC":
            row_exceptions = validate_row_internal(row, idx, channel, content_maps, zecom_maps, allowed_genders, allowed_statuses)
        else:
            row_exceptions = validate_row_post(row, idx, channel, content_maps, zecom_maps, check_live_images, allowed_genders, allowed_statuses)
            
        sk = _clean_sku(row.get("sku", ""))
        raw_size = clean_str(row.get("size", ""))
        sz_corrected = correct_size(raw_size).strip().lower()
        
        if (sk, sz_corrected) in duplicate_skus_sizes:
            row_exceptions.append({
                "Source File": row.get("_source_file", "Unknown File"),
                "Row Number": row.get("_original_row_number", idx + 2),
                "Article Number": clean_str(row.get("article_number", "")),
                "Product Name": clean_str(row.get("product_name", "")),
                "Field": "SKU & Size",
                "Value": f"SKU: {sk}, Size: {raw_size}",
                "Severity": "Warning",
                "Message": f"Duplicate record: product with SKU '{sk}' and corrected size '{correct_size(raw_size)}' is uploaded multiple times."
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
        src_clean["_match_key"] = src_clean[match_column] + " | " + src_clean["size"].astype(str).str.strip().apply(correct_size).str.lower()
        live_clean["_match_key"] = live_clean[match_column] + " | " + live_clean["size"].astype(str).str.strip().apply(correct_size).str.lower()
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
                src_field = field
                live_field = field
                
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

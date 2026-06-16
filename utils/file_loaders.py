import io
import re
import zipfile
import urllib.parse
import pandas as pd
import numpy as np
import streamlit as st

# Synonyms for auto-mapping columns
COLUMN_SYNONYMS = {
    "article_number": [
        "article number", "article no", "article", "sku", "product sku", 
        "seller sku", "article_number", "art no", "art_no", "item code", 
        "item_code", "style code", "style_code", "style number", "style_no"
    ],
    "ecommerce_status": [
        "e-commerce status", "ecommerce status", "status", "ecom status", 
        "listing status", "ecom_status", "channel status", "status_ecom",
        "active status", "listing_status"
    ],
    "launch_date": [
        "launch date", "launch_date", "date launch", "release date", 
        "launch date (dd/mm/yyyy)", "launch date (yyyy-mm-dd)", "launch_dates",
        "launching date", "start date"
    ],
    "gender": [
        "gender", "sex", "target group", "division", "genders", "target_group"
    ],
    "product_name": [
        "product name", "product_name", "name", "title", "item name", 
        "item_name", "description", "product title", "product_title"
    ],
    "color_name": [
        "color name", "color_name", "color", "colour", "color_no", 
        "color number", "color_description", "color description"
    ],
    "size": [
        "size", "size_code", "size code", "sizing", "product size", 
        "size_name", "size name"
    ],
    "quantity": [
        "quantity", "qty", "stock", "inventory", "quantity available", 
        "available qty", "quantity_available", "current stock", "stock_qty"
    ],
    "price": [
        "price", "retail price", "selling price", "amount", "msrp", 
        "price list", "unit price", "selling_price", "retail_price"
    ],
    "images": [
        "images", "image", "image url", "image_url", "image urls", 
        "image 1", "image link", "image_link", "product images", 
        "image_urls", "image_links"
    ],
    "size_chart": [
        "size chart", "size_chart", "size chart url", "size_chart_url", 
        "size chart link", "chart", "size_chart_link"
    ]
}

CANONICAL_LABELS = {
    "article_number": "Article Number",
    "ecommerce_status": "E-commerce Status",
    "launch_date": "Launch Date",
    "gender": "Gender",
    "product_name": "Product Name",
    "color_name": "Color Name",
    "size": "Size",
    "quantity": "Quantity",
    "price": "Price",
    "images": "Images",
    "size_chart": "Size Chart"
}

# ── General Helper Utilities ──────────────────────────────────────────────────

def _safe_str(val):
    if val is None:
        return ""
    if isinstance(val, (pd.Series, np.ndarray)):
        if len(val) == 0:
            return ""
        val = val.iloc[0] if hasattr(val, "iloc") else val[0]
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

def _normalise_cols(df):
    df.columns = [_safe_str(c) for c in df.columns]
    return df

def _normalise_article_no(val):
    s = _safe_str(val)
    if not s:
        return ""
    s = s.strip().upper()
    s = re.sub(r'[\s\-]+', '_', s)
    s = s.strip('_')
    return s

def _ecom_status_from_val(val, future_launch):
    if bool(future_launch):
        return "Inactive (No Future launch)"
    s = _safe_str(val).upper()
    if s in ("YES", "Y"):
        return "Active"
    return "Inactive"

def parse_google_sheets_url(url: str) -> str:
    if "docs.google.com/spreadsheets" not in url:
        return url
    try:
        id_match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
        if not id_match:
            return url
        spreadsheet_id = id_match.group(1)
        
        gid = "0"
        parsed_url = urllib.parse.urlparse(url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        if "gid" in query_params:
            gid = query_params["gid"][0]
        elif parsed_url.fragment:
            fragment_params = urllib.parse.parse_qs(parsed_url.fragment)
            if "gid" in fragment_params:
                gid = fragment_params["gid"][0]
            else:
                gid_match = re.search(r"gid=(\d+)", parsed_url.fragment)
                if gid_match:
                    gid = gid_match.group(1)
        return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={gid}"
    except Exception as e:
        st.error(f"Error parsing Google Sheets URL: {e}")
        return url

# ── General File Reader ───────────────────────────────────────────────────────

def _read_file(file, header_row=0, skiprows=None):
    if file is None:
        return pd.DataFrame()
    
    if isinstance(file, str):
        filename = file
        with open(file, 'rb') as f:
            raw = f.read()
    else:
        filename = getattr(file, "name", "unknown.csv")
        raw = file.read()
        file.seek(0)

    name = filename.lower()
    try:
        if name.endswith(".csv"):
            return pd.read_csv(io.BytesIO(raw), header=header_row, skiprows=skiprows, dtype=str)
        try:
            import python_calamine
            return pd.read_excel(io.BytesIO(raw), header=header_row, skiprows=skiprows, dtype=str, engine="calamine")
        except ImportError:
            return pd.read_excel(io.BytesIO(raw), header=header_row, skiprows=skiprows, dtype=str)
    except Exception:
        return pd.DataFrame()

def load_file_to_df(file_or_path, filename: str = None) -> pd.DataFrame:
    return _read_file(file_or_path)

def load_google_sheet(url: str) -> pd.DataFrame:
    csv_url = parse_google_sheets_url(url)
    return pd.read_csv(csv_url, dtype=str)

def _read_zip(file, header_row=0, skiprows=None):
    raw = file.read()
    file.seek(0)
    frames = []
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        for name in zf.namelist():
            if name.lower().endswith((".xlsx", ".xls", ".csv")):
                with zf.open(name) as f:
                    data = f.read()
                    try:
                        if name.lower().endswith(".csv"):
                            df = pd.read_csv(io.BytesIO(data), header=header_row, skiprows=skiprows, dtype=str)
                        else:
                            try:
                                import python_calamine
                                df = pd.read_excel(io.BytesIO(data), header=header_row, skiprows=skiprows, dtype=str, engine="calamine")
                            except ImportError:
                                df = pd.read_excel(io.BytesIO(data), header=header_row, skiprows=skiprows, dtype=str)
                        frames.append(df)
                    except Exception:
                        continue
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

# ── 10 Channel Specific Reading Methods ───────────────────────────────────────

def load_lazada(file, country):
    if file is None:
        return pd.DataFrame()
    df = _read_file(file, header_row=0)
    if df.empty:
        return pd.DataFrame()
    df = _normalise_cols(df)
    df = df.iloc[3:].reset_index(drop=True)
    
    col_map = {"SellerSKU": "SKU", "Quantity": "MP Stock", "status": "MP Status", "price": "MP Price", "name": "MP Product Name"}
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
    if "SKU" not in df.columns:
        return pd.DataFrame()
        
    df["Marketplace"] = "Lazada " + country
    df["SKU"] = df["SKU"].apply(_clean_sku)
    df = df[df["SKU"] != ""].copy()
    if "MP Stock" in df.columns:
        df["MP Stock"] = pd.to_numeric(df["MP Stock"].apply(_safe_str), errors="coerce").fillna(0)
    else:
        df["MP Stock"] = 0
    if "MP Price" in df.columns:
        df["MP Price"] = pd.to_numeric(df["MP Price"].apply(_safe_str), errors="coerce").fillna(0.0)
    return df

def _find_sku_col(df):
    for c in ["SKU", "Variation SKU", "Parent SKU", "Seller SKU", "SellerSKU", "ParentSKU", "VariationSKU"]:
        if c in df.columns:
            return c
    for c in df.columns:
        if "sku" in c.lower():
            return c
    return None

def _find_pid_col(df):
    for c in ["Product ID", "ProductID", "product_id", "product id"]:
        if c in df.columns:
            return c
    for c in df.columns:
        if "product" in c.lower() and "id" in c.lower():
            return c
    return None

def _parse_shopee_single(raw_bytes, filename_lower):
    import warnings
    if filename_lower.endswith(".csv"):
        try:
            df = pd.read_csv(io.BytesIO(raw_bytes), header=2, dtype=str)
            df = _normalise_cols(df)
            df = df.iloc[3:].reset_index(drop=True)
            df = df.dropna(how="all").reset_index(drop=True)
            return df
        except Exception:
            return pd.DataFrame()

    engines = []
    try:
        import python_calamine
        engines.append("calamine")
    except ImportError:
        pass
    engines.append("openpyxl")

    for engine in engines:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                df = pd.read_excel(io.BytesIO(raw_bytes), header=2, dtype=str, engine=engine)
            if df is None or df.empty:
                continue
            df = _normalise_cols(df)
            if len(df) > 3:
                df = df.iloc[3:].reset_index(drop=True)
            df = df.dropna(how="all").reset_index(drop=True)
            cols_lower = [c.lower() for c in df.columns]
            if any("sku" in c for c in cols_lower) or any("product" in c for c in cols_lower):
                if len(df) > 0:
                    return df
        except Exception:
            continue

    try:
        import openpyxl
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            wb = openpyxl.load_workbook(io.BytesIO(raw_bytes), data_only=True, read_only=True)
            ws = wb.active
            rows_data = []
            for row in ws.iter_rows(values_only=True):
                rows_data.append(list(row))
            wb.close()
        if len(rows_data) < 7:
            return pd.DataFrame()
        header = [str(v).strip() if v is not None else "" for v in rows_data[2]]
        data_rows = rows_data[6:]
        df = pd.DataFrame(data_rows, columns=header)
        df = df.astype(str).replace("None", "")
        df = _normalise_cols(df)
        df = df.dropna(how="all").reset_index(drop=True)
        cols_lower = [c.lower() for c in df.columns]
        if any("sku" in c for c in cols_lower) or any("product" in c for c in cols_lower):
            return df
    except Exception:
        pass

    return pd.DataFrame()

def _load_shopee_raw(file):
    if file is None:
        return pd.DataFrame()
    name = file.name.lower()
    raw = file.read()
    file.seek(0)
    
    if name.endswith(".zip"):
        frames = []
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as zf:
                for entry in sorted(zf.namelist()):
                    if entry.lower().endswith((".xlsx", ".xls", ".csv")):
                        with zf.open(entry) as f:
                            entry_bytes = f.read()
                        df = _parse_shopee_single(entry_bytes, entry.lower())
                        if not df.empty:
                            frames.append(df)
        except Exception:
            return pd.DataFrame()
        if not frames:
            return pd.DataFrame()
        combined = pd.concat(frames, ignore_index=True)
        return _normalise_cols(combined)
    else:
        return _parse_shopee_single(raw, name)

def load_shopee_stock(file, country):
    df = _load_shopee_raw(file)
    if df.empty:
        return pd.DataFrame()

    pid_col = _find_pid_col(df)
    if pid_col and pid_col != "Product ID":
        df = df.rename(columns={pid_col: "Product ID"})

    sku_col = None
    for c in ["SKU", "Variation SKU", "VariationSKU", "Seller SKU", "SellerSKU"]:
        if c in df.columns:
            sku_col = c
            break
    if sku_col is None:
        for c in df.columns:
            cl = c.lower()
            if "sku" in cl and "parent" not in cl:
                sku_col = c
                break

    parent_col = None
    for c in ["Parent SKU", "ParentSKU", "parent_sku", "parent sku"]:
        if c in df.columns:
            parent_col = c
            break

    stock_col = None
    for c in ["Stock", "MP Stock", "Available Stock", "Current Stock", "Quantity"]:
        if c in df.columns:
            stock_col = c
            break

    price_col = None
    for c in ["Price", "MP Price", "Price List", "Unit Price"]:
        if c in df.columns:
            price_col = c
            break

    if sku_col:
        df["SKU"] = df[sku_col].apply(_clean_sku)
    else:
        df["SKU"] = ""

    if parent_col:
        mask_blank = df["SKU"] == ""
        df.loc[mask_blank, "SKU"] = df.loc[mask_blank, parent_col].apply(_clean_sku)

    df = df[df["SKU"].str.fullmatch(r"\d{13}", na=False)].copy().reset_index(drop=True)
    if df.empty:
        return pd.DataFrame()

    if stock_col and stock_col != "MP Stock":
        df = df.rename(columns={stock_col: "MP Stock"})
    if price_col and price_col != "MP Price":
        df = df.rename(columns={price_col: "MP Price"})

    df["Marketplace"] = "Shopee " + country
    if "MP Stock" in df.columns:
        df["MP Stock"] = pd.to_numeric(df["MP Stock"].apply(_safe_str), errors="coerce").fillna(0)
    else:
        df["MP Stock"] = 0
    if "MP Price" in df.columns:
        df["MP Price"] = pd.to_numeric(df["MP Price"].apply(_safe_str), errors="coerce").fillna(0.0)

    return df

def load_shopee_status(file, country):
    df = _load_shopee_raw(file)
    if df.empty:
        return pd.DataFrame()

    pid_col = _find_pid_col(df)
    if pid_col:
        if pid_col != "Product ID":
            df = df.rename(columns={pid_col: "Product ID"})
        df["Product ID"] = df["Product ID"].apply(_safe_str)
    else:
        df["Product ID"] = ""

    df["MP Status"] = df["Product ID"].apply(
        lambda x: "Active" if _safe_str(x) not in ("", "nan", "none") else "Inactive"
    )

    sku_col = None
    for c in ["SKU", "Variation SKU", "Seller SKU"]:
        if c in df.columns:
            sku_col = c
            break
    if sku_col is None:
        for c in df.columns:
            if "sku" in c.lower() and "parent" not in c.lower():
                sku_col = c
                break

    if sku_col and sku_col != "SKU":
        df = df.rename(columns={sku_col: "SKU"})

    parent_col = None
    for c in ["Parent SKU", "ParentSKU", "parent_sku", "parent sku"]:
        if c in df.columns:
            parent_col = c
            break

    if "SKU" in df.columns:
        df["SKU"] = df["SKU"].apply(_clean_sku)
        if parent_col:
            mask_blank = df["SKU"] == ""
            df.loc[mask_blank, "SKU"] = df.loc[mask_blank, parent_col].apply(_clean_sku)
        
        has_13 = df["SKU"].str.fullmatch(r'\d{13}', na=False).any()
        if has_13:
            df = df[df["SKU"].str.fullmatch(r'\d{13}', na=False)].copy()
    else:
        df["SKU"] = ""

    df["Marketplace"] = "Shopee " + country
    return df.reset_index(drop=True)

def load_zalora_stock(file, country):
    if file is None:
        return pd.DataFrame()
    df = _read_file(file)
    if df.empty:
        return pd.DataFrame()
    df = _normalise_cols(df)
    
    sku_col = None
    for c in ["SellerSku", "SellerSKU", "Seller Sku", "Seller SKU", "SKU"]:
        if c in df.columns:
            sku_col = c
            break
    if sku_col is None:
        for c in df.columns:
            if "sku" in c.lower() or "seller" in c.lower():
                sku_col = c
                break
    if sku_col is None:
        return pd.DataFrame()
    if sku_col != "SKU":
        df = df.rename(columns={sku_col: "SKU"})
        
    qty_col = None
    for c in ["Quantity", "Stock", "MP Stock", "quantity", "stock"]:
        if c in df.columns:
            qty_col = c
            break
    if qty_col and qty_col != "MP Stock":
        df = df.rename(columns={qty_col: "MP Stock"})
        
    price_col = None
    for c in ["Price", "MP Price", "price", "unit price"]:
        if c in df.columns:
            price_col = c
            break
    if price_col and price_col != "MP Price":
        df = df.rename(columns={price_col: "MP Price"})

    df["SKU"] = df["SKU"].apply(_clean_sku)
    df["Marketplace"] = "Zalora " + country
    df = df[df["SKU"] != ""].copy()
    if "MP Stock" in df.columns:
        df["MP Stock"] = pd.to_numeric(df["MP Stock"].apply(_safe_str), errors="coerce").fillna(0)
    else:
        df["MP Stock"] = 0
    if "MP Price" in df.columns:
        df["MP Price"] = pd.to_numeric(df["MP Price"].apply(_safe_str), errors="coerce").fillna(0.0)
    return df

def load_zalora_status(file, country):
    if file is None:
        return pd.DataFrame()
    df = _read_file(file)
    if df.empty:
        return pd.DataFrame()
    df = _normalise_cols(df)
    
    sku_col = None
    for c in ["SellerSku", "SellerSKU", "Seller Sku", "Seller SKU", "SKU"]:
        if c in df.columns:
            sku_col = c
            break
    if sku_col is None:
        for c in df.columns:
            if "sku" in c.lower() or "seller" in c.lower():
                sku_col = c
                break
    if sku_col is None:
        return pd.DataFrame()
    if sku_col != "SKU":
        df = df.rename(columns={sku_col: "SKU"})
        
    status_col = None
    for c in ["Status", "MP Status", "status", "mp_status"]:
        if c in df.columns:
            status_col = c
            break
    if status_col is None:
        for c in df.columns:
            if "status" in c.lower():
                status_col = c
                break
    if status_col and status_col != "MP Status":
        df = df.rename(columns={status_col: "MP Status"})
        
    if "MP Status" in df.columns:
        df["MP Status"] = df["MP Status"].apply(_safe_str).str.strip().str.capitalize()
    else:
        df["MP Status"] = "Unknown"
        
    df["SKU"] = df["SKU"].apply(_clean_sku)
    df["Marketplace"] = "Zalora " + country
    return df[df["SKU"] != ""].copy()

def _load_tiktok_raw(file):
    if file is None:
        return pd.DataFrame()
    df = _read_file(file, header_row=2)
    if df.empty:
        return pd.DataFrame()
    df = _normalise_cols(df)
    if len(df) > 2:
        df = df.iloc[2:].reset_index(drop=True)
    return df

def _load_tiktok_file(file, status_label):
    if file is None:
        return pd.DataFrame()
    df = _load_tiktok_raw(file)
    if df.empty:
        return pd.DataFrame()
        
    sku_col = None
    for c in ["Seller SKU", "SellerSKU", "SKU", "seller sku"]:
        if c in df.columns:
            sku_col = c
            break
    if sku_col is None:
        for c in df.columns:
            if "sku" in c.lower():
                sku_col = c
                break
    if sku_col is None:
        return pd.DataFrame()
        
    pid_col = None
    for c in ["Product ID", "ProductID", "product_id", "product id"]:
        if c in df.columns:
            pid_col = c
            break
            
    qty_col = None
    for c in ["Quantity", "Stock", "quantity", "stock", "Available Stock"]:
        if c in df.columns:
            qty_col = c
            break
            
    price_col = None
    for c in ["Price", "price", "Retail Price"]:
        if c in df.columns:
            price_col = c
            break

    out = pd.DataFrame()
    out["SKU"] = df[sku_col].apply(_clean_sku)
    if pid_col:
        out["Product ID"] = df[pid_col].apply(_safe_str)
    else:
        out["Product ID"] = ""
        
    out["MP Stock"] = pd.to_numeric(
        df[qty_col].apply(_safe_str) if qty_col else pd.Series([0] * len(df)),
        errors="coerce"
    ).fillna(0)
    out["MP Price"] = pd.to_numeric(
        df[price_col].apply(_safe_str) if price_col else pd.Series([0.0] * len(df)),
        errors="coerce"
    ).fillna(0.0)
    
    out["MP Status"]   = status_label
    out["Marketplace"] = "TikTok MY"
    return out[out["SKU"] != ""].copy()

def load_tiktok(active_file, inactive_file):
    active   = _load_tiktok_file(active_file,   "Active")
    inactive = _load_tiktok_file(inactive_file, "Inactive")
    if active.empty and inactive.empty:
        return pd.DataFrame()
    combined = pd.concat([active, inactive], ignore_index=True)
    combined = combined.sort_values(
        "MP Status",
        key=lambda x: x.map({"Active": 0, "Inactive": 1}),
    )
    combined = combined.drop_duplicates(subset=["SKU"], keep="first")
    return combined.reset_index(drop=True)

# ── Content File Loader (maps EAN to SKU and extracts multiple size columns)
def load_content(file):
    if file is None:
        return pd.DataFrame()
    df = _read_file(file)
    if df.empty:
        return pd.DataFrame()
    df = _normalise_cols(df)
    
    if "EAN" in df.columns and "SKU" not in df.columns:
        df = df.rename(columns={"EAN": "SKU"})
        
    art_col = None
    for c in ["Article No", "Color_No", "Color_No.1", "ArticleNo", "Article Number"]:
        if c in df.columns:
            art_col = c
            break
    if art_col is None:
        for c in df.columns:
            if "article" in c.lower() or "color" in c.lower():
                art_col = c
                break
    if art_col and art_col != "Article No":
        df = df.rename(columns={art_col: "Article No"})
        
    # Auto-detect UK Size column
    uk_col = next((c for c in df.columns if "uk" in c.lower() and "size" in c.lower()), 
                  next((c for c in df.columns if "uk" in c.lower()), None))
    df["uk_size"] = df[uk_col].apply(_safe_str) if uk_col else ""
    
    # Auto-detect US Size column
    us_col = next((c for c in df.columns if "us" in c.lower() and "size" in c.lower()), 
                  next((c for c in df.columns if "us" in c.lower()), None))
    df["us_size"] = df[us_col].apply(_safe_str) if us_col else ""
    
    # Auto-detect Russian Size column
    rus_col = next((c for c in df.columns if ("rus" in c.lower() or "russian" in c.lower()) and "size" in c.lower()), 
                   next((c for c in df.columns if "rus" in c.lower() or "russian" in c.lower()), None))
    df["rus_size"] = df[rus_col].apply(_safe_str) if rus_col else ""

    if "SKU" in df.columns:
        df["SKU"] = df["SKU"].apply(_clean_sku)
    if "Article No" in df.columns:
        df["Article No"] = df["Article No"].apply(_safe_str)
        
    return df

# ── zEcom Loader (extracts launch dates, ecom statuses, and RRP Price)
def load_zecom(file, country="PH"):
    if file is None:
        return pd.DataFrame()
    raw = file.read()
    name = file.name.lower()
    file.seek(0)

    article_col_by_country = {
        "PH": ["PIM Article#", "PIM Article #", "Article No", "ArticleNo"],
        "MY": ["Style#", "STYLE#", "style#", "Article No", "PIM Article#"],
        "SG": ["STYLE#", "Style#", "style#", "Article No", "PIM Article#"],
    }
    preferred_article_cols = article_col_by_country.get(country, ["Article No"])
    preferred_rows = [2, 1, 0, 3] if country == "PH" else [3, 2, 1, 0]

    try:
        if name.endswith(".csv"):
            raw_df = pd.read_csv(io.BytesIO(raw), header=None, dtype=str)
        else:
            try:
                import python_calamine
                raw_df = pd.read_excel(io.BytesIO(raw), header=None, dtype=str, engine="calamine")
            except ImportError:
                raw_df = pd.read_excel(io.BytesIO(raw), header=None, dtype=str)
    except Exception:
        return pd.DataFrame()

    if raw_df.empty:
        return pd.DataFrame()

    header_idx = None
    for r_idx in preferred_rows:
        if r_idx < len(raw_df):
            row_vals = [_safe_str(x) for x in raw_df.iloc[r_idx]]
            row_lower = [v.lower() for v in row_vals]
            expected  = [c.lower() for c in preferred_article_cols]
            if any(e in row_lower for e in expected) or any("article" in c or "pim" in c or "style" in c for c in row_lower):
                header_idx = r_idx
                break

    if header_idx is None:
        for r_idx in range(min(6, len(raw_df))):
            row_vals = [_safe_str(x) for x in raw_df.iloc[r_idx]]
            row_lower = [v.lower() for v in row_vals]
            expected  = [c.lower() for c in preferred_article_cols]
            if any(e in row_lower for e in expected) or any("article" in c or "pim" in c or "style" in c for c in row_lower):
                header_idx = r_idx
                break

    if header_idx is None:
        header_idx = preferred_rows[0] if preferred_rows[0] < len(raw_df) else 0

    df = raw_df.iloc[header_idx + 1:].copy()
    df.columns = [_safe_str(x) for x in raw_df.iloc[header_idx]]
    df = df.loc[:, ~df.columns.duplicated()].copy()
    df = df.reset_index(drop=True)
    
    first_col = df.columns[0]
    df = df[df[first_col].apply(_safe_str) != first_col].copy()
    df = df.reset_index(drop=True)

    article_col = None
    for c in preferred_article_cols:
        if c in df.columns:
            article_col = c
            break
    if article_col is None:
        for c in df.columns:
            if "style" in c.lower() or "article" in c.lower() or "pim" in c.lower():
                article_col = c
                break
    if article_col and article_col != "Article No":
        df = df.rename(columns={article_col: "Article No"})

    if "Article No" in df.columns:
        df = df[df["Article No"].apply(_safe_str) != ""].copy()
        df = df.reset_index(drop=True)

    # Auto-detect RRP Price column
    rrp_col = next((c for c in df.columns if "rrp" in c.lower() or ("retail" in c.lower() and "price" in c.lower())), None)
    if rrp_col:
        df["rrp_price"] = df[rrp_col].apply(_safe_str)
    else:
        df["rrp_price"] = ""

    launch_col = None
    for c in ["Launch Dates", "Launch Date", "LaunchDate", "Launch"]:
        if c in df.columns:
            launch_col = c
            break
    if launch_col is None:
        for c in df.columns:
            if "launch" in c.lower():
                launch_col = c
                break
    if launch_col and launch_col != "Launch Date":
        df = df.rename(columns={launch_col: "Launch Date"})

    today = pd.Timestamp.today().normalize()
    if "Launch Date" in df.columns:
        df["Launch Date"] = pd.to_datetime(df["Launch Date"], errors="coerce")
        df["Future Launch"] = df["Launch Date"].apply(
            lambda d: True if pd.notna(d) and d > today else False
        )
    else:
        df["Future Launch"] = False

    mp_keywords = {
        "lazada":  "Ecom_Lazada",
        "shopee":  "Ecom_Shopee",
        "zalora":  "Ecom_Zalora",
        "tiktok":  "Ecom_TikTok",
    }
    for col in df.columns:
        if col in ("Article No", "Launch Date", "Future Launch", "rrp_price"):
            continue
        col_l = col.lower()
        for mp_key, ecom_name in mp_keywords.items():
            if mp_key in col_l and ecom_name not in df.columns:
                df[ecom_name] = df.apply(
                    lambda row, c=col: _ecom_status_from_val(
                        row[c], row["Future Launch"]
                    ),
                    axis=1,
                )
                break

    return df

# ── Auto column mapping functions ─────────────────────────────────────────────

def auto_map_columns(columns: list) -> dict:
    mapping = {}
    normalized_cols = {col.strip().lower(): col for col in columns}
    
    for canonical, synonyms in COLUMN_SYNONYMS.items():
        found = False
        for syn in synonyms:
            if syn in normalized_cols:
                mapping[canonical] = normalized_cols[syn]
                found = True
                break
        
        if not found:
            for col_raw in columns:
                col_lower = col_raw.strip().lower()
                for syn in synonyms:
                    if syn in col_lower or col_lower in syn:
                        mapping[canonical] = col_raw
                        found = True
                        break
                if found:
                    break
                    
        if not found:
            mapping[canonical] = None
            
    return mapping

def standardize_dataframe(df: pd.DataFrame, mapping: dict, source_name: str = "Uploaded File") -> pd.DataFrame:
    standard_df = pd.DataFrame()
    standard_df["_original_row_number"] = df.index + 2
    standard_df["_source_file"] = [source_name] * len(df)
    
    for canonical, file_col in mapping.items():
        if file_col and file_col in df.columns:
            col_data = df[file_col]
            if isinstance(col_data, pd.DataFrame):
                col_data = col_data.iloc[:, 0]
            standard_df[canonical] = col_data
        else:
            standard_df[canonical] = pd.NA
            
    return standard_df

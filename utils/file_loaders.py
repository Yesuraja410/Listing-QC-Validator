import io
import re
import urllib.parse
import pandas as pd
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

def parse_google_sheets_url(url: str) -> str:
    """
    Parses a Google Sheets sharing URL and converts it to a direct CSV download URL.
    Returns the original URL if it does not match Google Sheets format.
    """
    if "docs.google.com/spreadsheets" not in url:
        return url
        
    try:
        # Match spreadsheet ID
        id_match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
        if not id_match:
            return url
        spreadsheet_id = id_match.group(1)
        
        # Match GID (sheet ID) from URL query or fragment
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
                # Direct check in case fragment contains gid=XXX without standard query structure
                gid_match = re.search(r"gid=(\d+)", parsed_url.fragment)
                if gid_match:
                    gid = gid_match.group(1)
                    
        return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={gid}"
    except Exception as e:
        st.error(f"Error parsing Google Sheets URL: {e}")
        return url

def load_file_to_df(file_or_path, filename: str = None) -> pd.DataFrame:
    """
    Loads an Excel or CSV file from a file object (Streamlit upload) or a file path into a DataFrame.
    """
    if filename is None:
        if isinstance(file_or_path, str):
            filename = file_or_path
        else:
            filename = getattr(file_or_path, "name", "unknown.csv")
            
    ext = filename.split(".")[-1].lower()
    
    if ext == "csv":
        # Handle file-like objects vs file paths
        if hasattr(file_or_path, "read"):
            file_or_path.seek(0)
            return pd.read_csv(file_or_path)
        else:
            return pd.read_csv(file_or_path)
    elif ext in ["xlsx", "xls"]:
        if hasattr(file_or_path, "read"):
            file_or_path.seek(0)
            return pd.read_excel(file_or_path)
        else:
            return pd.read_excel(file_or_path)
    else:
        raise ValueError(f"Unsupported file format: {ext}. Please upload .xlsx, .xls, or .csv files.")

def load_google_sheet(url: str) -> pd.DataFrame:
    """
    Downloads and loads a Google Sheet directly into a DataFrame.
    """
    csv_url = parse_google_sheets_url(url)
    # pd.read_csv can fetch directly from HTTP URLs
    return pd.read_csv(csv_url)

def auto_map_columns(columns: list) -> dict:
    """
    Maps list of file columns to canonical names using synonym matches.
    Returns a dictionary of canonical_name -> file_column.
    """
    mapping = {}
    normalized_cols = {col.strip().lower(): col for col in columns}
    
    for canonical, synonyms in COLUMN_SYNONYMS.items():
        found = False
        # Try exact match first
        for syn in synonyms:
            if syn in normalized_cols:
                mapping[canonical] = normalized_cols[syn]
                found = True
                break
        
        # If not found, try partial match (case-insensitive substring match)
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
                    
        # If still not found, set mapping to None
        if not found:
            mapping[canonical] = None
            
    return mapping

def standardize_dataframe(df: pd.DataFrame, mapping: dict, source_name: str = "Uploaded File") -> pd.DataFrame:
    """
    Prepares raw DataFrame for validation by renaming columns to canonical names
    and appending index indicators for Excel row correspondence.
    """
    standard_df = df.copy()
    
    # Track the original row number (Excel is 1-indexed, plus 1 for header row = index + 2)
    standard_df["_original_row_number"] = standard_df.index + 2
    standard_df["_source_file"] = source_name
    
    # Selectively rename and keep columns based on mapping
    rename_dict = {}
    cols_to_keep = ["_original_row_number", "_source_file"]
    
    for canonical, file_col in mapping.items():
        if file_col and file_col in standard_df.columns:
            rename_dict[file_col] = canonical
            # If a column was mapped to multiple canonical fields, make copies
            if canonical not in standard_df.columns:
                standard_df[canonical] = standard_df[file_col]
            cols_to_keep.append(canonical)
        else:
            # Create a column of NaN if it's missing in mapping
            standard_df[canonical] = pd.NA
            cols_to_keep.append(canonical)
            
    # Apply bulk rename
    standard_df = standard_df.rename(columns=rename_dict)
    
    # Retain only standard columns and tracking columns
    return standard_df[cols_to_keep]

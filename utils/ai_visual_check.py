"""
AI Visual Verification for Listing Post QC.

This module answers a DIFFERENT question than the perceptual-hash image
comparison elsewhere in this app. Hashing answers "is this the exact same
image as before" (pixel identity) - it cannot tell you whether an image
actually *depicts* the right thing. This module uses a vision model
(Google Gemini) to answer the semantic question instead:

  - Does the product image actually show the stated Color Name?
  - Is the product image's apparent gender/category consistent with the
    Product Name (e.g. Product Name says "Unisex", does the photo show a
    unisex-styled shoe, not obviously a kids' shoe)?
  - Is the Size Chart image the RIGHT KIND of size chart for this product's
    category (e.g. an adult shoe size chart, not a bag/apparel/kids chart)?

Because vision API calls cost money and take 1-3 seconds each, this is
designed to run on a SAMPLE (one row per unique Product Name + Color Name
combination) rather than every row - see sample_rows_for_visual_check().
"""

import base64
import io
import json
import re
import threading
import concurrent.futures
from typing import Dict, List, Optional, Tuple

import pandas as pd
import requests

GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

_MAX_IMAGE_BYTES = 2_000_000  # 2 MB is plenty for a vision model to judge color/category
_REQUEST_TIMEOUT = (5, 20)    # (connect, read) seconds - vision calls take longer than a hash download

# ── Category/gender extraction from Product Name ────────────────────────────

_CATEGORY_PATTERNS = [
    ("Youth", [r"\byouth\b"]),
    ("Junior", [r"\bjunior\b", r"\bjr\b"]),
    ("Kids", [r"\bkids?\b", r"\binfant\b", r"\btoddler\b", r"\bchildren'?s\b"]),
    ("Women", [r"\bwomen'?s\b", r"\bwomens\b", r"\bwmns\b"]),
    ("Men", [r"\bmen'?s\b", r"\bmens\b"]),
    ("Unisex", [r"\bunisex\b"]),
]

def extract_category_from_name(product_name: str) -> str:
    """
    Pulls the gender/age category (Unisex, Men, Women, Kids, Junior, Youth)
    out of a Product Name string, e.g.
    "[NEW] PUMA Unisex FUTURE 9 MATCH FG/AG Football Shoes Youth (Red)"
    -> matches BOTH "Unisex" and "Youth"; the more specific age-group term
    wins over the generic "Unisex" when both are present, since that's the
    stronger signal for which size chart is actually correct.
    """
    s = (product_name or "").lower()
    found = []
    for label, patterns in _CATEGORY_PATTERNS:
        if any(re.search(p, s) for p in patterns):
            found.append(label)
    if not found:
        return "Unknown"
    # Age-specific terms (Youth/Junior/Kids) are more decisive for size-chart
    # correctness than the generic "Unisex" adult-style descriptor.
    for specific in ("Youth", "Junior", "Kids"):
        if specific in found:
            return specific
    return found[0]


# ── Sampling ──────────────────────────────────────────────────────────────

def sample_rows_for_visual_check(df: pd.DataFrame, product_col: str = "product_name", color_col: str = "color_name") -> pd.DataFrame:
    """
    Returns one representative row per unique (Product Name, Color Name)
    combination - this is the whole point of "spot-check a sample" rather
    than running a vision call on every single SKU/variant row, since
    every SKU under the same product+color shares the same images.
    """
    if df.empty or product_col not in df.columns or color_col not in df.columns:
        return df.iloc[0:0]
    work = df.copy()
    work["_pname_key"] = work[product_col].astype(str).str.strip().str.lower()
    work["_color_key"] = work[color_col].astype(str).str.strip().str.lower()
    work = work[(work["_pname_key"] != "") & (work["_color_key"] != "")]
    sampled = work.drop_duplicates(subset=["_pname_key", "_color_key"], keep="first")
    return sampled.drop(columns=["_pname_key", "_color_key"], errors="ignore")


# ── Image fetch helper ───────────────────────────────────────────────────

_DOWNLOAD_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def _fetch_image_b64(url: str) -> Optional[Tuple[str, str]]:
    """Downloads an image and returns (base64_data, mime_type), or None on failure."""
    url = (url or "").strip()
    if not url:
        return None
    try:
        resp = requests.get(url, timeout=_REQUEST_TIMEOUT, stream=True, headers=_DOWNLOAD_HEADERS)
        resp.raise_for_status()
        chunks = []
        total = 0
        for chunk in resp.iter_content(chunk_size=65536):
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total >= _MAX_IMAGE_BYTES:
                break
        resp.close()
        data = b"".join(chunks)
        if not data:
            return None
        content_type = resp.headers.get("Content-Type", "image/jpeg").split(";")[0].strip()
        if not content_type.startswith("image/"):
            content_type = "image/jpeg"
        return base64.b64encode(data).decode("ascii"), content_type
    except Exception:
        return None


# ── Gemini call ──────────────────────────────────────────────────────────

_PROMPT_TEMPLATE = """You are performing a quality-control check on a PUMA e-commerce product listing.

Product Name: {product_name}
Expected Color Name: {color_name}
Expected Product Category/Gender: {category}

The FIRST image attached is the PRIMARY PRODUCT PHOTO for this listing.
The SECOND image attached (if provided) is the SIZE CHART image used for this listing.

Answer strictly as JSON with exactly this structure and nothing else:
{{
  "color_match": true or false,
  "color_reason": "one short sentence",
  "category_match": true or false,
  "category_reason": "one short sentence - is this size chart the correct type for this product's category (e.g. an adult unisex/men's/women's shoe size chart is WRONG for a Youth/Kids/Junior product, and a shoe size chart is WRONG for a bag/apparel product)?"
}}

If no size chart image was provided, set category_match to false and category_reason to "No size chart image provided."
"""

def call_gemini_vision(api_key: str, image_url: str, size_chart_url: str, product_name: str, color_name: str, category: str) -> Dict:
    """
    Sends the primary product image + size chart image to Gemini and asks it
    to judge color/category correctness. Returns a dict with keys:
    color_match, color_reason, category_match, category_reason, error
    (error is None on success, or a short string describing what went wrong).
    """
    result = {"color_match": None, "color_reason": "", "category_match": None, "category_reason": "", "error": None}

    img = _fetch_image_b64(image_url)
    if img is None:
        result["error"] = "Could not download primary product image."
        return result

    parts = [{"text": _PROMPT_TEMPLATE.format(product_name=product_name, color_name=color_name, category=category)}]
    img_data, img_mime = img
    parts.append({"inline_data": {"mime_type": img_mime, "data": img_data}})

    sc = _fetch_image_b64(size_chart_url)
    if sc is not None:
        sc_data, sc_mime = sc
        parts.append({"inline_data": {"mime_type": sc_mime, "data": sc_data}})

    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {"response_mime_type": "application/json"}
    }

    try:
        resp = requests.post(
            GEMINI_ENDPOINT,
            params={"key": api_key},
            json=payload,
            timeout=_REQUEST_TIMEOUT
        )
        if resp.status_code == 400:
            result["error"] = "Gemini rejected the request (check API key / image format)."
            return result
        if resp.status_code == 403:
            result["error"] = "Gemini API key invalid or lacks permission."
            return result
        if resp.status_code == 429:
            result["error"] = "Gemini rate limit hit - try again shortly."
            return result
        resp.raise_for_status()
        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(text)
        result["color_match"] = bool(parsed.get("color_match"))
        result["color_reason"] = str(parsed.get("color_reason", "")).strip()
        result["category_match"] = bool(parsed.get("category_match"))
        result["category_reason"] = str(parsed.get("category_reason", "")).strip()
    except (KeyError, IndexError, json.JSONDecodeError):
        result["error"] = "Could not parse Gemini's response."
    except requests.exceptions.RequestException as e:
        result["error"] = f"Network error calling Gemini: {e}"
    except Exception as e:
        result["error"] = f"Unexpected error: {e}"

    return result


def _verdict_from_result(res: Dict) -> Tuple[str, str]:
    """Turns a raw Gemini result dict into a short (verdict, notes) pair for the report."""
    if res.get("error"):
        return "Not Checked", res["error"]
    issues = []
    if res.get("color_match") is False:
        issues.append(f"Color mismatch: {res.get('color_reason', '')}")
    if res.get("category_match") is False:
        issues.append(f"Size chart/category mismatch: {res.get('category_reason', '')}")
    if issues:
        return "Mismatch Found", " | ".join(issues)
    return "OK", "Images available as per the color name and Size chart available as per the category."


def run_ai_visual_checks(
    df: pd.DataFrame,
    api_key: str,
    image_col: str = "images",
    size_chart_col: str = "size_chart",
    product_col: str = "product_name",
    color_col: str = "color_name",
    max_workers: int = 5,
    progress_callback=None
) -> pd.DataFrame:
    """
    Runs the AI visual check on a SAMPLE (one row per unique Product Name +
    Color Name) and returns the full df with two new columns added:
    'AI Visual Check' (OK / Mismatch Found / Not Checked / Not Sampled) and
    'AI Visual Check Notes'. Rows outside the sample get 'Not Sampled' so
    it's clear at a glance which rows were actually spot-checked.
    """
    out = df.copy()
    out["AI Visual Check"] = "Not Sampled"
    out["AI Visual Check Notes"] = ""

    if not api_key:
        out["AI Visual Check"] = "Not Checked"
        out["AI Visual Check Notes"] = "No Gemini API key provided."
        return out

    sample = sample_rows_for_visual_check(out, product_col=product_col, color_col=color_col)
    if sample.empty:
        return out

    def _first_image_url(cell) -> str:
        s = str(cell or "").strip()
        if not s:
            return ""
        return re.split(r"[,;]", s)[0].strip()

    jobs = []
    for idx in sample.index:
        row = out.loc[idx]
        img_url = _first_image_url(row.get(image_col, ""))
        sc_url = str(row.get(size_chart_col, "") or "").strip()
        pname = str(row.get(product_col, "") or "").strip()
        cname = str(row.get(color_col, "") or "").strip()
        category = extract_category_from_name(pname)
        jobs.append((idx, img_url, sc_url, pname, cname, category))

    total = len(jobs)
    done = 0
    done_lock = threading.Lock()

    def _worker(job):
        idx, img_url, sc_url, pname, cname, category = job
        if not img_url:
            return idx, {"error": "No product image URL available for this row."}
        res = call_gemini_vision(api_key, img_url, sc_url, pname, cname, category)
        return idx, res

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(_worker, job) for job in jobs]
        for f in concurrent.futures.as_completed(futures):
            idx, res = f.result()
            verdict, notes = _verdict_from_result(res)
            out.at[idx, "AI Visual Check"] = verdict
            out.at[idx, "AI Visual Check Notes"] = notes
            with done_lock:
                done += 1
                if progress_callback:
                    progress_callback(done, total)

    return out

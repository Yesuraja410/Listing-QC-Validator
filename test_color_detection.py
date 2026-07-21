import io
import re
import colorsys
import numpy as np
from PIL import Image

COLOR_KEYWORDS = {
    "black": ["black", "blk", "dark", "noir", "schwarz"],
    "white": ["white", "wht", "snow", "blanc", "weiss", "ivory", "off-white", "off white"],
    "red": ["red", "scarlet", "crimson", "burgundy", "maroon", "ruby", "rouge"],
    "blue": ["blue", "navy", "royal", "cyan", "azure", "indigo", "bleu"],
    "green": ["green", "olive", "lime", "emerald", "vert"],
    "yellow": ["yellow", "gold", "golden", "jaune"],
    "pink": ["pink", "magenta", "rose", "fuchsia"],
    "grey": ["grey", "gray", "silver", "charcoal", "slate", "gris"],
    "orange": ["orange", "coral", "peach"],
    "purple": ["purple", "violet", "plum", "lilac"],
    "brown": ["brown", "tan", "chocolate", "bronze"],
    "beige": ["beige", "cream", "khaki", "nude"]
}

def extract_expected_colors(color_name: str) -> list:
    if not color_name:
        return []
    cn_low = str(color_name).lower()
    found_colors = []
    for std_color, syns in COLOR_KEYWORDS.items():
        for syn in syns:
            if re.search(r'\b' + re.escape(syn) + r'\b', cn_low):
                if std_color not in found_colors:
                    found_colors.append(std_color)
                break
    return found_colors

def analyze_image_dominant_colors(img_input) -> dict:
    try:
        if isinstance(img_input, bytes):
            img = Image.open(io.BytesIO(img_input)).convert('RGB')
        elif isinstance(img_input, Image.Image):
            img = img_input.convert('RGB')
        else:
            return {}

        img = img.resize((64, 64), Image.Resampling.LANCZOS)
        arr = np.array(img, dtype=float) / 255.0  # Shape (64, 64, 3)

        # Reshape to list of pixels (N, 3)
        pixels = arr.reshape(-1, 3)

        # Exclude near-white background pixels (R>0.92, G>0.92, B>0.92)
        bg_mask = (pixels[:, 0] > 0.92) & (pixels[:, 1] > 0.92) & (pixels[:, 2] > 0.92)
        prod_pixels = pixels[~bg_mask]

        if len(prod_pixels) < 50:
            # If almost all background, lower threshold slightly
            bg_mask = (pixels[:, 0] > 0.97) & (pixels[:, 1] > 0.97) & (pixels[:, 2] > 0.97)
            prod_pixels = pixels[~bg_mask]

        if len(prod_pixels) == 0:
            return {"white": 1.0}

        counts = {c: 0 for c in COLOR_KEYWORDS.keys()}
        total_p = len(prod_pixels)

        for r, g, b in prod_pixels:
            h, s, v = colorsys.rgb_to_hsv(r, g, b)
            h_deg = h * 360.0

            if v < 0.25:
                counts["black"] += 1
            elif s < 0.12 and v > 0.85:
                counts["white"] += 1
            elif s < 0.15:
                counts["grey"] += 1
            elif h_deg < 15 or h_deg >= 345:
                if s > 0.2 and v > 0.2:
                    counts["red"] += 1
                else:
                    counts["grey"] += 1
            elif 15 <= h_deg < 45:
                if v < 0.5 and s > 0.2:
                    counts["brown"] += 1
                else:
                    counts["orange"] += 1
            elif 45 <= h_deg < 70:
                counts["yellow"] += 1
            elif 70 <= h_deg < 165:
                counts["green"] += 1
            elif 165 <= h_deg < 260:
                counts["blue"] += 1
            elif 260 <= h_deg < 315:
                counts["purple"] += 1
            elif 315 <= h_deg < 345:
                counts["pink"] += 1

        color_shares = {c: count / total_p for c, count in counts.items() if count > 0}
        return dict(sorted(color_shares.items(), key=lambda item: item[1], reverse=True))

    except Exception as e:
        print(f"Color analysis error: {e}")
        return {}

def verify_color_name_against_image(color_name: str, img_input) -> tuple:
    expected_colors = extract_expected_colors(color_name)
    if not expected_colors:
        return True, "No standard color keyword found in Color Name."

    detected_shares = analyze_image_dominant_colors(img_input)
    if not detected_shares:
        return True, "Unable to analyze image colors."

    top_colors = list(detected_shares.keys())[:3]
    top_str = ", ".join([f"{c} ({detected_shares[c]*100:.1f}%)" for c in top_colors])

    # Check if any expected color is present with significant presence (> 5% share)
    matched = any(c in detected_shares and detected_shares[c] >= 0.05 for c in expected_colors)

    if matched:
        return True, f"Color match confirmed (Expected: {', '.join(expected_colors)}, Detected: {top_str})"
    else:
        # Check if black vs white conflict specifically
        return False, f"Color mismatch: Stated Color Name '{color_name}' expects [{', '.join(expected_colors)}], but image dominant colors are [{top_str}]."

# Test runner
if __name__ == "__main__":
    print("Testing color extraction...")
    print("PUMA Black ->", extract_expected_colors("PUMA Black"))
    print("Alpine Snow-For All Time Red ->", extract_expected_colors("Alpine Snow-For All Time Red"))
    print("PUMA Black-Puma White ->", extract_expected_colors("PUMA Black-Puma White"))
    
    # Create synthetic solid black image on white background
    img = Image.new('RGB', (100, 100), (255, 255, 255))
    for x in range(20, 80):
        for y in range(20, 80):
            img.putpixel((x, y), (15, 15, 20)) # Dark black shoe
            
    ok, msg = verify_color_name_against_image("PUMA Black", img)
    print("Test 1 (Black Shoe):", ok, msg)
    
    ok, msg = verify_color_name_against_image("PUMA White", img)
    print("Test 2 (White Shoe check on Black Shoe):", ok, msg)

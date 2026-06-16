import unittest
import pandas as pd
import datetime
from validators import (
    validate_row_internal, 
    validate_row_post, 
    validate_dataframe, 
    compare_source_and_live
)

class TestValidators(unittest.TestCase):
    
    def setUp(self):
        # Sample base valid row data
        self.valid_internal_row = pd.Series({
            "article_number": "ART-101",
            "ecommerce_status": "Active",
            "launch_date": "2026-06-20",
            "gender": "Men",
            "product_name": "Men's Leather Running Shoes Black Edition",
            "color_name": "Black",
            "size": "42",
            "quantity": 100,
            "price": 89.99,
            "_original_row_number": 2,
            "_source_file": "test_file.csv"
        })
        
        self.valid_post_row = pd.Series({
            "article_number": "ART-101",
            "ecommerce_status": "Active",
            "launch_date": "2026-06-20",
            "gender": "Men",
            "product_name": "Men's Leather Running Shoes Black Edition",
            "color_name": "Black",
            "size": "42",
            "quantity": 100,
            "price": 89.99,
            "images": "https://example.com/img1.jpg, https://example.com/img2.png",
            "size_chart": "https://example.com/men-shoes-sizechart.jpg",
            "_original_row_number": 2,
            "_source_file": "test_file.csv"
        })

    def test_valid_internal_row(self):
        excs = validate_row_internal(self.valid_internal_row, 0)
        self.assertEqual(len(excs), 0, f"Expected 0 exceptions, found: {excs}")

    def test_invalid_price(self):
        row = self.valid_internal_row.copy()
        row["price"] = -10.0
        excs = validate_row_internal(row, 0)
        price_excs = [e for e in excs if e["Field"] == "Price"]
        self.assertTrue(len(price_excs) > 0)
        self.assertIn("greater than zero", price_excs[0]["Message"])

    def test_invalid_quantity(self):
        row = self.valid_internal_row.copy()
        row["quantity"] = 5.5
        excs = validate_row_internal(row, 0)
        qty_excs = [e for e in excs if e["Field"] == "Quantity"]
        self.assertTrue(len(qty_excs) > 0)
        self.assertIn("whole integer", qty_excs[0]["Message"])

    def test_gender_mismatch_male_female_keyword(self):
        # Gender is Men, but Product Name contains "women"
        row = self.valid_internal_row.copy()
        row["product_name"] = "Women's Lightweight Jogger Pants"
        row["gender"] = "Men"
        excs = validate_row_internal(row, 0)
        gender_excs = [e for e in excs if e["Field"] == "Product Name"]
        self.assertTrue(len(gender_excs) > 0)
        self.assertIn("Gender mismatch", gender_excs[0]["Message"])

    def test_gender_mismatch_female_male_keyword(self):
        # Gender is Women, but Product Name contains "boy"
        row = self.valid_internal_row.copy()
        row["product_name"] = "Slim Fit Boy Denim Jeans"
        row["gender"] = "Women"
        excs = validate_row_internal(row, 0)
        gender_excs = [e for e in excs if e["Field"] == "Product Name"]
        self.assertTrue(len(gender_excs) > 0)
        self.assertIn("Gender mismatch", gender_excs[0]["Message"])

    def test_invalid_launch_date_format(self):
        row = self.valid_internal_row.copy()
        row["launch_date"] = "invalid-date-string"
        excs = validate_row_internal(row, 0)
        date_excs = [e for e in excs if e["Field"] == "Launch Date"]
        self.assertTrue(len(date_excs) > 0)
        self.assertIn("invalid format", date_excs[0]["Message"])

    def test_valid_post_row(self):
        excs = validate_row_post(self.valid_post_row, 0, check_live_images=False)
        self.assertEqual(len(excs), 0, f"Expected 0 exceptions, found: {excs}")

    def test_missing_size_chart(self):
        row = self.valid_post_row.copy()
        row["size_chart"] = ""
        excs = validate_row_post(row, 0, check_live_images=False)
        sc_excs = [e for e in excs if e["Field"] == "Size Chart"]
        self.assertTrue(len(sc_excs) > 0)
        self.assertIn("missing", sc_excs[0]["Message"])

    def test_invalid_image_url(self):
        row = self.valid_post_row.copy()
        row["images"] = "not_a_valid_url"
        excs = validate_row_post(row, 0, check_live_images=False)
        img_excs = [e for e in excs if e["Field"] == "Images"]
        self.assertTrue(len(img_excs) > 0)
        self.assertIn("not a valid URL format", img_excs[0]["Message"])

    def test_dataframe_validation_aggregations(self):
        # Create a test dataframe with 1 valid row and 1 invalid row, and a duplicate
        df = pd.DataFrame([
            self.valid_internal_row.to_dict(),
            self.valid_internal_row.to_dict(), # Duplicate Article + Size
            {
                "article_number": "ART-102",
                "ecommerce_status": "Active",
                "launch_date": "2026-06-20",
                "gender": "Kids",
                "product_name": "Kids Sandals",
                "color_name": "Blue",
                "size": "28",
                "quantity": -5,  # Error
                "price": 0.0,    # Error
                "_original_row_number": 4,
                "_source_file": "test_file.csv"
            }
        ])
        
        exc_df, val_df, logs = validate_dataframe(df, qc_stage="Internal QC")
        
        # Check logs are populated
        self.assertTrue(len(logs) > 0)
        
        # Check status column is correct
        self.assertEqual(val_df.iloc[0]["_qc_status"], "Warning") # Has duplicate warning
        self.assertEqual(val_df.iloc[2]["_qc_status"], "Failed")  # Has errors
        
        # Verify exceptions count
        # Row 0 and Row 1 are duplicates. So they each get 1 warning = 2 warnings
        # Row 2 has negative stock and 0 price = 2 errors
        self.assertEqual(len(exc_df), 4)

    def test_live_comparison_engine(self):
        # Create a source dataframe
        src_df = pd.DataFrame([
            {
                "article_number": "ART-COMP",
                "size": "M",
                "product_name": "Cotton Polo Shirt",
                "price": 29.99,
                "quantity": 50,
                "ecommerce_status": "Active",
                "images": "https://example.com/polo.jpg",
                "size_chart": "https://example.com/polo-chart.jpg",
                "_original_row_number": 2,
                "_source_file": "src.csv"
            },
            {
                "article_number": "ART-MISSING-LIVE",
                "size": "L",
                "product_name": "Cotton Tee",
                "price": 19.99,
                "quantity": 20,
                "ecommerce_status": "Active",
                "_original_row_number": 3,
                "_source_file": "src.csv"
            }
        ])
        
        # Create a live dataframe
        live_df = pd.DataFrame([
            {
                "article_number": "ART-COMP",
                "size": "M",
                "product_name": "Cotton Polo Shirt",
                "price": 34.99, # Price mismatch
                "quantity": 50,
                "ecommerce_status": "Active",
                "images": "https://example.com/polo.jpg",
                "size_chart": "https://example.com/polo-chart.jpg",
                "_original_row_number": 2,
                "_source_file": "live.csv"
            },
            {
                "article_number": "ART-EXTRA-LIVE",
                "size": "S",
                "product_name": "Extra Cargo Pants",
                "price": 49.99,
                "quantity": 10,
                "ecommerce_status": "Active",
                "_original_row_number": 3,
                "_source_file": "live.csv"
            }
        ])
        
        comp_df, metrics = compare_source_and_live(src_df, live_df)
        
        # Check metrics
        self.assertEqual(metrics["Total Keys Analyzed"], 3) # ART-COMP|M, ART-MISSING-LIVE|L, ART-EXTRA-LIVE|S
        self.assertEqual(metrics["Items with Mismatches"], 1) # price mismatch on ART-COMP|M
        self.assertEqual(metrics["Missing in Live Listings"], 1) # ART-MISSING-LIVE|L
        self.assertEqual(metrics["Extra Live Listings"], 1) # ART-EXTRA-LIVE|S

if __name__ == '__main__':
    unittest.main()

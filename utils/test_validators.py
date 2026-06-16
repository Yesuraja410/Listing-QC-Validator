import unittest
import pandas as pd
import datetime
from validators import (
    validate_row_internal, 
    validate_row_post, 
    validate_dataframe, 
    compare_source_and_live,
    build_content_maps,
    build_zecom_maps
)

class TestValidators(unittest.TestCase):
    
    def setUp(self):
        # 1. Mock Content Reference File Data
        self.mock_content_df = pd.DataFrame([
            {
                "SKU": "4069161482557",
                "Article No": "404620_07",
                "uk_size": "42",
                "gender": "Men"
            },
            {
                "SKU": "4069161482595",
                "Article No": "404620_07",
                "uk_size": "43",
                "gender": "Men"
            },
            {
                "SKU": "4069161482999",
                "Article No": "531103_03",
                "uk_size": "S",
                "gender": "Women"
            }
        ])
        
        # 2. Mock zEcom Reference File Data
        # PH columns: Article No, Launch Date, Ecom_Shopee, Ecom_Lazada
        self.mock_zecom_df = pd.DataFrame([
            {
                "Article No": "404620_07",
                "Launch Date": pd.to_datetime("2026-06-20"),
                "Ecom_Shopee": "Active",
                "Ecom_Lazada": "Inactive"
            },
            {
                "Article No": "531103_03",
                "Launch Date": pd.to_datetime("2026-06-15"),
                "Ecom_Shopee": "Inactive",
                "Ecom_Lazada": "Active"
            }
        ])
        
        # Build maps
        self.content_maps = build_content_maps(self.mock_content_df)
        self.zecom_maps_shopee = build_zecom_maps(self.mock_zecom_df, "Shopee PH")
        
        # 3. Base Valid Row in Upload Sheet (to be validated)
        self.valid_upload_row = pd.Series({
            "article_number": "404620_07",
            "sku": "4069161482557",
            "ecommerce_status": "Active",
            "launch_date": "2026-06-20",
            "gender": "Men",
            "product_name": "Men's Leather Running Shoes Black Edition",
            "color_name": "Black",
            "size": "42",  # Matches UK size 42 in Content File
            "quantity": 100,
            "price": 89.99,
            "_original_row_number": 2,
            "_source_file": "test_upload.csv"
        })

    def test_valid_row_cross_reference(self):
        # Validation for Shopee PH where article 404620_07 is active
        excs = validate_row_internal(
            self.valid_upload_row, 0, 
            content_maps=self.content_maps, 
            zecom_maps=self.zecom_maps_shopee
        )
        self.assertEqual(len(excs), 0, f"Expected 0 exceptions on valid row, found: {excs}")

    def test_size_mismatch_against_uk_size(self):
        # Size uploaded is 44, but UK size for SKU 4069161482557 is 42
        row = self.valid_upload_row.copy()
        row["size"] = "44"
        excs = validate_row_internal(
            row, 0, 
            content_maps=self.content_maps, 
            zecom_maps=self.zecom_maps_shopee
        )
        size_excs = [e for e in excs if e["Field"] == "Size"]
        self.assertTrue(len(size_excs) > 0)
        self.assertIn("does not match UK size '42'", size_excs[0]["Message"])

    def test_size_fallback_to_article_no(self):
        # SKU is not in Content File, but Article is 404620_07.
        # Upload size 44 is not in [42, 43] (the UK sizes of 404620_07).
        row = self.valid_upload_row.copy()
        row["sku"] = "4069161482777"  # Unknown SKU
        row["size"] = "44"             # Invalid Size for this Article
        excs = validate_row_internal(
            row, 0, 
            content_maps=self.content_maps, 
            zecom_maps=self.zecom_maps_shopee
        )
        # We expect a SKU warning (unknown) and a Size mismatch error
        size_excs = [e for e in excs if e["Field"] == "Size"]
        self.assertTrue(len(size_excs) > 0)
        self.assertIn("is not in the list of valid UK sizes", size_excs[0]["Message"])

    def test_article_mismatch_against_ean_mapping(self):
        # SKU is mapped to 404620_07, but uploaded Article No is 531103_03
        row = self.valid_upload_row.copy()
        row["article_number"] = "531103_03"
        excs = validate_row_internal(
            row, 0, 
            content_maps=self.content_maps, 
            zecom_maps=self.zecom_maps_shopee
        )
        art_excs = [e for e in excs if e["Field"] == "Article Number"]
        self.assertTrue(len(art_excs) > 0)
        self.assertIn("Article mismatch", art_excs[0]["Message"])

    def test_ecommerce_status_mismatch_against_zecom(self):
        # For Shopee PH, article 404620_07 is Active.
        # But if we validate for Lazada PH (where it is Inactive):
        zecom_maps_lazada = build_zecom_maps(self.mock_zecom_df, "Lazada PH")
        excs = validate_row_internal(
            self.valid_upload_row, 0, 
            content_maps=self.content_maps, 
            zecom_maps=zecom_maps_lazada
        )
        status_excs = [e for e in excs if e["Field"] == "E-commerce Status"]
        self.assertTrue(len(status_excs) > 0)
        self.assertIn("status is 'Active' but zEcom File defines it as 'Inactive'", status_excs[0]["Message"])

    def test_launch_date_mismatch_against_zecom(self):
        # zEcom Launch date is 2026-06-20. Uploaded launch date is 2026-06-10.
        row = self.valid_upload_row.copy()
        row["launch_date"] = "2026-06-10"
        excs = validate_row_internal(
            row, 0, 
            content_maps=self.content_maps, 
            zecom_maps=self.zecom_maps_shopee
        )
        date_excs = [e for e in excs if e["Field"] == "Launch Date"]
        self.assertTrue(len(date_excs) > 0)
        self.assertIn("Launch Date mismatch", date_excs[0]["Message"])

    def test_gender_mismatch_against_content(self):
        # Content File gender for SKU is Men, but Uploaded gender is Women
        row = self.valid_upload_row.copy()
        row["gender"] = "Women"
        # Avoid gender-product title mismatch warning by using unisex title
        row["product_name"] = "Running Shoes Black Edition" 
        excs = validate_row_internal(
            row, 0, 
            content_maps=self.content_maps, 
            zecom_maps=self.zecom_maps_shopee
        )
        gender_excs = [e for e in excs if e["Field"] == "Gender"]
        self.assertTrue(len(gender_excs) > 0)
        self.assertIn("Uploaded gender 'Women' does not match Content File gender 'Men'", gender_excs[0]["Message"])

    def test_dataframe_validation_aggregations(self):
        # Create a test dataframe with 1 valid row and 1 invalid row
        df = pd.DataFrame([
            self.valid_upload_row.to_dict(),
            {
                "article_number": "531103_03",
                "sku": "4069161482999",
                "ecommerce_status": "Active",  # Mismatch (zEcom Ecom_Shopee is Inactive)
                "launch_date": "2026-06-15",
                "gender": "Women",
                "product_name": "Women's Lightweight Jogger Pants",
                "color_name": "Grey",
                "size": "M",  # Mismatch (UK size is S)
                "quantity": 10,
                "price": 49.99,
                "_original_row_number": 3,
                "_source_file": "test_upload.csv"
            }
        ])
        
        exc_df, val_df, logs = validate_dataframe(
            df, 
            qc_stage="Internal QC",
            channel="Shopee PH",
            content_df=self.mock_content_df,
            zecom_df=self.mock_zecom_df
        )
        
        # Verify exceptions count
        # Row 1: Valid (0 issues)
        # Row 2: Mismatches in Ecom Status (Active vs Inactive) + Size (M vs S) = 2 exceptions
        self.assertEqual(len(exc_df), 2)
        self.assertEqual(val_df.iloc[0]["_qc_status"], "Passed")
        self.assertEqual(val_df.iloc[1]["_qc_status"], "Failed")

if __name__ == '__main__':
    unittest.main()

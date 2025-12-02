#!/usr/bin/env python3
"""
Test against the exact Axentra payload schema
Validates that field stripping matches the "Cut" annotations exactly
"""

import json
import sys
import os

# Add parent directory to path to import lambda function
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda'))

from webhook_processor import strip_fields, calculate_payload_hash, detect_event_type

# Exact schema from Axentra
EXACT_SCHEMA = {
    "products": {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "name": "Test Product",
        "description": "Test Description",
        "dosage_instructions": "Take with food",
        "manufacturer": "Test Manufacturer",
        "needs_prescription": False,
        "needs_telemed": True,
        "store_id": "223e4567-e89b-12d3-a456-426614174000",
        "user_id": "323e4567-e89b-12d3-a456-426614174000",
        "category_ids": ["423e4567-e89b-12d3-a456-426614174000"],
        "status": "active",
        "created_at": "2024-01-01T00:00:00Z",  # CUT
        "updated_at": "2024-01-02T00:00:00Z",  # CUT
        "archived_at": None,  # CUT
        "product_variants": [
            {
                "id": "523e4567-e89b-12d3-a456-426614174000",
                "product_id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Variant 1",
                "variant_name": "Standard",
                "price": 29.99,
                "image_url": "https://example.com/image.jpg",  # CUT
                "sku": "TEST-SKU-001",
                "stock_quantity": 100,  # CUT
                "is_default": True,  # CUT
                "stockStatus": "In Stock",  # CUT
                "status": "NEW",
                "archived_at": None,  # CUT
                "lab_test_codes_id": ["623e4567-e89b-12d3-a456-426614174000"],  # CUT
                "service_product_id": "723e4567-e89b-12d3-a456-426614174000",  # CUT
                "cpr_price": 25.99  # CUT
            }
        ],
        "categories": [
            {
                "id": "823e4567-e89b-12d3-a456-426614174000",
                "name": "Category 1",
                "is_featured": True,
                "store_id": "223e4567-e89b-12d3-a456-426614174000",
                "user_id": "323e4567-e89b-12d3-a456-426614174000",  # CUT
                "created_at": "2024-01-01T00:00:00Z",  # CUT
                "last_modified": "2024-01-02T00:00:00Z",  # CUT
                "image": "https://example.com/cat.jpg"  # CUT
            }
        ]
    }
}

# Fields that should be stripped (from "Cut" annotations)
FIELDS_TO_STRIP = {
    "products": ["created_at", "updated_at", "archived_at"],
    "product_variants": [
        "image_url", "stock_quantity", "is_default", "stockStatus",
        "lab_test_codes_id", "service_product_id", "cpr_price", "archived_at"
    ],
    "categories": ["user_id", "created_at", "last_modified", "image"]
}

# Fields that should be kept
# Note: user_id is kept in products but stripped from categories
FIELDS_TO_KEEP = {
    "products": [
        "id", "name", "description", "dosage_instructions", "manufacturer",
        "needs_prescription", "needs_telemed", "store_id", "user_id",  # user_id kept in products
        "category_ids", "status", "product_variants", "categories"
    ],
    "product_variants": [
        "id", "product_id", "name", "variant_name", "price", "sku", "status"
    ],
    "categories": ["id", "name", "is_featured", "store_id"]
}


def test_exact_schema_stripping():
    """Test field stripping against exact Axentra schema"""
    print("Testing against exact Axentra payload schema...")
    print()
    
    stripped = strip_fields(EXACT_SCHEMA)
    
    # Verify products fields
    print("Checking products fields...")
    for field in FIELDS_TO_STRIP["products"]:
        assert field not in stripped["products"], f"❌ {field} should be stripped from products"
        print(f"  ✅ {field} correctly stripped from products")
    
    for field in FIELDS_TO_KEEP["products"]:
        if field in ["product_variants", "categories"]:
            continue  # These are nested, check separately
        assert field in stripped["products"], f"❌ {field} should be kept in products"
        print(f"  ✅ {field} correctly kept in products")
    
    # Verify product_variants fields
    print("\nChecking product_variants fields...")
    variant = stripped["products"]["product_variants"][0]
    for field in FIELDS_TO_STRIP["product_variants"]:
        assert field not in variant, f"❌ {field} should be stripped from product_variants"
        print(f"  ✅ {field} correctly stripped from product_variants")
    
    for field in FIELDS_TO_KEEP["product_variants"]:
        assert field in variant, f"❌ {field} should be kept in product_variants"
        print(f"  ✅ {field} correctly kept in product_variants")
    
    # Verify categories fields
    print("\nChecking categories fields...")
    category = stripped["products"]["categories"][0]
    for field in FIELDS_TO_STRIP["categories"]:
        assert field not in category, f"❌ {field} should be stripped from categories"
        print(f"  ✅ {field} correctly stripped from categories")
    
    for field in FIELDS_TO_KEEP["categories"]:
        assert field in category, f"❌ {field} should be kept in categories"
        print(f"  ✅ {field} correctly kept in categories")
    
    print("\n✅ All field stripping matches exact schema requirements!")
    return True


def test_schema_structure():
    """Verify the payload structure matches the schema"""
    print("\nVerifying schema structure...")
    
    products = EXACT_SCHEMA["products"]
    
    # Check required top-level fields
    assert "id" in products, "products.id is required"
    assert "name" in products, "products.name is required"
    assert "product_variants" in products, "products.product_variants is required"
    assert "categories" in products, "products.categories is required"
    
    # Check product_variants structure
    assert isinstance(products["product_variants"], list), "product_variants should be array"
    variant = products["product_variants"][0]
    assert "id" in variant, "product_variants[].id is required"
    assert "product_id" in variant, "product_variants[].product_id is required"
    assert "price" in variant, "product_variants[].price is required"
    
    # Check categories structure
    assert isinstance(products["categories"], list), "categories should be array"
    category = products["categories"][0]
    assert "id" in category, "categories[].id is required"
    assert "name" in category, "categories[].name is required"
    
    print("✅ Schema structure is valid")
    return True


def test_hash_with_exact_schema():
    """Test hash calculation with exact schema"""
    print("\nTesting hash calculation with exact schema...")
    
    hash1 = calculate_payload_hash(EXACT_SCHEMA)
    hash2 = calculate_payload_hash(EXACT_SCHEMA)
    
    assert hash1 == hash2, "Same payload should produce same hash"
    assert len(hash1) == 64, "Hash should be 64 characters (SHA-256)"
    
    print(f"✅ Hash calculation works (hash: {hash1[:16]}...)")
    return True


def test_event_detection_with_exact_schema():
    """Test event type detection with exact schema"""
    print("\nTesting event type detection with exact schema...")
    
    event_type = detect_event_type(EXACT_SCHEMA)
    assert event_type in ["product_create", "product_update"], \
        f"Expected product_create/update, got {event_type}"
    
    # Test delete detection
    delete_payload = {"products": {"id": "123", "archived_at": "2024-01-01T00:00:00Z"}}
    delete_type = detect_event_type(delete_payload)
    assert delete_type == "product_delete", f"Expected product_delete, got {delete_type}"
    
    print(f"✅ Event type detection works (detected: {event_type})")
    return True


def main():
    """Run all exact schema tests"""
    print("=" * 60)
    print("Exact Axentra Schema Validation Tests")
    print("=" * 60)
    print()
    
    tests = [
        test_exact_schema_stripping,
        test_schema_structure,
        test_hash_with_exact_schema,
        test_event_detection_with_exact_schema
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"\n❌ Test failed: {e}\n")
            failed += 1
        except Exception as e:
            print(f"\n❌ Test error: {e}\n")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed > 0:
        sys.exit(1)
    else:
        print("✅ All exact schema tests passed!")


if __name__ == "__main__":
    main()


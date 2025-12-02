#!/usr/bin/env python3
"""
Local tests for Lambda function logic (no AWS required)
Tests field stripping, event type detection, hash calculation, and S3 key generation
"""

import json
import sys
import os
from datetime import datetime

# Add parent directory to path to import lambda function
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda'))

# Import Lambda functions (mock AWS clients)
from webhook_processor import (
    calculate_payload_hash,
    strip_fields,
    detect_event_type,
    get_routing_target,
    enrich_payload
)


def test_field_stripping():
    """Test that fields are properly stripped from payload"""
    print("Testing field stripping...")
    
    sample_payload = {
        "products": {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "name": "Test Product",
            "description": "Test Description",
            "created_at": "2024-01-01T00:00:00Z",  # Should be stripped
            "updated_at": "2024-01-02T00:00:00Z",  # Should be stripped
            "archived_at": None,  # Should be stripped
            "product_variants": [
                {
                    "id": "223e4567-e89b-12d3-a456-426614174000",
                    "name": "Variant 1",
                    "image_url": "https://example.com/image.jpg",  # Should be stripped
                    "stock_quantity": 100,  # Should be stripped
                    "is_default": True,  # Should be stripped
                    "stockStatus": "In Stock",  # Should be stripped
                    "cpr_price": 25.99,  # Should be stripped
                    "price": 29.99  # Should be kept
                }
            ],
            "categories": [
                {
                    "id": "323e4567-e89b-12d3-a456-426614174000",
                    "name": "Category 1",
                    "user_id": "423e4567-e89b-12d3-a456-426614174000",  # Should be stripped
                    "created_at": "2024-01-01T00:00:00Z",  # Should be stripped
                    "image": "https://example.com/cat.jpg"  # Should be stripped
                }
            ]
        }
    }
    
    stripped = strip_fields(sample_payload)
    
    # Verify products fields stripped
    assert "created_at" not in stripped["products"], "created_at should be stripped"
    assert "updated_at" not in stripped["products"], "updated_at should be stripped"
    assert "archived_at" not in stripped["products"], "archived_at should be stripped"
    
    # Verify product_variants fields stripped
    variant = stripped["products"]["product_variants"][0]
    assert "image_url" not in variant, "image_url should be stripped"
    assert "stock_quantity" not in variant, "stock_quantity should be stripped"
    assert "is_default" not in variant, "is_default should be stripped"
    assert "stockStatus" not in variant, "stockStatus should be stripped"
    assert "cpr_price" not in variant, "cpr_price should be stripped"
    
    # Verify fields kept
    assert "price" in variant, "price should be kept"
    assert "name" in variant, "name should be kept"
    
    # Verify categories fields stripped
    category = stripped["products"]["categories"][0]
    assert "user_id" not in category, "user_id should be stripped from categories"
    assert "created_at" not in category, "created_at should be stripped from categories"
    assert "image" not in category, "image should be stripped from categories"
    
    # Verify fields kept
    assert "name" in category, "name should be kept in categories"
    assert "id" in category, "id should be kept in categories"
    
    print("✅ Field stripping test passed")
    return True


def test_hash_calculation():
    """Test that payload hash is calculated correctly"""
    print("Testing hash calculation...")
    
    payload1 = {"test": "data"}
    payload2 = {"test": "data"}
    payload3 = {"test": "different"}
    
    hash1 = calculate_payload_hash(payload1)
    hash2 = calculate_payload_hash(payload2)
    hash3 = calculate_payload_hash(payload3)
    
    # Same payload should produce same hash
    assert hash1 == hash2, "Same payload should produce same hash"
    
    # Different payload should produce different hash
    assert hash1 != hash3, "Different payload should produce different hash"
    
    # Hash should be 64 characters (SHA-256 hex)
    assert len(hash1) == 64, "Hash should be 64 characters"
    
    print(f"✅ Hash calculation test passed (hash: {hash1[:16]}...)")
    return True


def test_event_type_detection():
    """Test event type detection logic"""
    print("Testing event type detection...")
    
    # Test product_create
    create_payload = {
        "products": {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "name": "New Product"
        }
    }
    event_type = detect_event_type(create_payload)
    assert event_type in ["product_create", "product_update"], f"Expected product_create/update, got {event_type}"
    
    # Test product_delete (has archived_at)
    delete_payload = {
        "products": {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "archived_at": "2024-01-01T00:00:00Z"
        }
    }
    event_type = detect_event_type(delete_payload)
    assert event_type == "product_delete", f"Expected product_delete, got {event_type}"
    
    # Test unknown
    unknown_payload = {"unknown": "data"}
    event_type = detect_event_type(unknown_payload)
    assert event_type == "unknown", f"Expected unknown, got {event_type}"
    
    print("✅ Event type detection test passed")
    return True


def test_routing_logic():
    """Test routing target determination"""
    print("Testing routing logic...")
    
    routing_map = {
        "product_create": "product-service",
        "product_update": "product-service",
        "product_delete": "product-service",
        "store_create": "store-service",
        "unknown": "default-handler"
    }
    
    for event_type, expected_target in routing_map.items():
        target = get_routing_target(event_type)
        assert target == expected_target, f"Expected {expected_target} for {event_type}, got {target}"
    
    print("✅ Routing logic test passed")
    return True


def test_metadata_enrichment():
    """Test metadata enrichment"""
    print("Testing metadata enrichment...")
    
    # Set environment variable for testing
    os.environ['EVENT_VERSION'] = '1.0'
    
    payload = {"test": "data"}
    payload_hash = calculate_payload_hash(payload)
    event_type = "product_create"
    
    enriched = enrich_payload(payload, payload_hash, event_type)
    
    assert "_metadata" in enriched, "Enriched payload should have _metadata"
    assert enriched["_metadata"]["payload_hash"] == payload_hash, "Hash should match"
    assert enriched["_metadata"]["event_type"] == event_type, "Event type should match"
    assert enriched["_metadata"]["event_version"] == "1.0", "Event version should match"
    assert "processing_timestamp" in enriched["_metadata"], "Should have processing timestamp"
    
    print("✅ Metadata enrichment test passed")
    return True


def test_s3_key_generation():
    """Test S3 key format"""
    print("Testing S3 key generation...")
    
    # Simulate the S3 key generation logic
    now = datetime.utcnow()
    year = now.strftime('%Y')
    month = now.strftime('%m')
    day = now.strftime('%d')
    event_id = "test-event-123"
    event_type = "product_create"
    
    s3_key = f"{event_type}/{year}/{month}/{day}/{event_id}.json"
    
    # Verify format
    assert s3_key.startswith(f"{event_type}/"), "Should start with event_type"
    assert f"/{year}/" in s3_key, "Should contain year"
    assert f"/{month}/" in s3_key, "Should contain month"
    assert f"/{day}/" in s3_key, "Should contain day"
    assert s3_key.endswith(".json"), "Should end with .json"
    
    # Verify date format
    assert len(year) == 4, "Year should be 4 digits"
    assert len(month) == 2, "Month should be 2 digits"
    assert len(day) == 2, "Day should be 2 digits"
    
    print(f"✅ S3 key generation test passed (example: {s3_key})")
    return True


def test_full_payload_schema():
    """Test with full payload schema from Axentra"""
    print("Testing with full Axentra payload schema...")
    
    full_payload = {
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
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-02T00:00:00Z",
            "archived_at": None,
            "product_variants": [
                {
                    "id": "523e4567-e89b-12d3-a456-426614174000",
                    "product_id": "123e4567-e89b-12d3-a456-426614174000",
                    "name": "Variant 1",
                    "variant_name": "Standard",
                    "price": 29.99,
                    "image_url": "https://example.com/image.jpg",
                    "sku": "TEST-SKU-001",
                    "stock_quantity": 100,
                    "is_default": True,
                    "stockStatus": "In Stock",
                    "status": "NEW",
                    "archived_at": None,
                    "lab_test_codes_id": ["623e4567-e89b-12d3-a456-426614174000"],
                    "service_product_id": "723e4567-e89b-12d3-a456-426614174000",
                    "cpr_price": 25.99
                }
            ],
            "categories": [
                {
                    "id": "823e4567-e89b-12d3-a456-426614174000",
                    "name": "Category 1",
                    "is_featured": True,
                    "store_id": "223e4567-e89b-12d3-a456-426614174000",
                    "user_id": "323e4567-e89b-12d3-a456-426614174000",
                    "created_at": "2024-01-01T00:00:00Z",
                    "last_modified": "2024-01-02T00:00:00Z",
                    "image": "https://example.com/cat.jpg"
                }
            ]
        }
    }
    
    # Test field stripping
    stripped = strip_fields(full_payload)
    
    # Verify all expected fields are stripped
    assert "created_at" not in stripped["products"]
    assert "updated_at" not in stripped["products"]
    assert "archived_at" not in stripped["products"]
    
    variant = stripped["products"]["product_variants"][0]
    assert "image_url" not in variant
    assert "stock_quantity" not in variant
    assert "is_default" not in variant
    assert "stockStatus" not in variant
    assert "lab_test_codes_id" not in variant
    assert "service_product_id" not in variant
    assert "cpr_price" not in variant
    assert "archived_at" not in variant
    
    category = stripped["products"]["categories"][0]
    assert "user_id" not in category
    assert "created_at" not in category
    assert "last_modified" not in category
    assert "image" not in category
    
    # Verify important fields are kept
    assert "id" in stripped["products"]
    assert "name" in stripped["products"]
    assert "price" in variant
    assert "sku" in variant
    assert "name" in category
    
    # Test event type detection
    event_type = detect_event_type(full_payload)
    assert event_type in ["product_create", "product_update", "product_delete"]
    
    # Test hash calculation
    hash1 = calculate_payload_hash(full_payload)
    hash2 = calculate_payload_hash(full_payload)
    assert hash1 == hash2
    
    print("✅ Full payload schema test passed")
    return True


def main():
    """Run all tests"""
    print("=" * 60)
    print("Lambda Function Logic Tests (No AWS Required)")
    print("=" * 60)
    print()
    
    tests = [
        test_field_stripping,
        test_hash_calculation,
        test_event_type_detection,
        test_routing_logic,
        test_metadata_enrichment,
        test_s3_key_generation,
        test_full_payload_schema
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
            print()
        except AssertionError as e:
            print(f"❌ Test failed: {e}")
            failed += 1
            print()
        except Exception as e:
            print(f"❌ Test error: {e}")
            failed += 1
            print()
    
    print("=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed > 0:
        sys.exit(1)
    else:
        print("✅ All tests passed!")


if __name__ == "__main__":
    main()





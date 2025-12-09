#!/usr/bin/env python3
"""
Tests for new simplified payload structures with explicit event_type
"""

import json
import sys
import os

# Mock boto3 before importing webhook_processor
class MockClient:
    def put_object(self, **kwargs):
        return {}
    def get_object(self, **kwargs):
        return {'Body': type('obj', (object,), {'read': lambda: b'{}'})()}
    def delete_object(self, **kwargs):
        return {}
    def publish(self, **kwargs):
        return {'MessageId': 'test-id'}

class MockBoto3:
    @staticmethod
    def client(service):
        return MockClient()
    @staticmethod
    def resource(service):
        class MockTable:
            def __init__(self, name):
                self.name = name
            def query(self, **kwargs):
                return {'Items': []}
            def put_item(self, **kwargs):
                return {}
        class MockDynamoDB:
            def Table(self, name):
                return MockTable(name)
        return MockDynamoDB()

sys.modules['boto3'] = MockBoto3()

# Add parent directory to path to import lambda function
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda'))

# Mock environment variables
os.environ['S3_RAW_AUDIT_BUCKET'] = 'test-bucket'
os.environ['S3_PROCESSED_BUCKET'] = 'test-processed-bucket'
os.environ['DYNAMODB_TABLE_NAME'] = 'test-table'

from webhook_processor import (
    detect_event_type,
    get_store_id,
    get_product_id,
    strip_fields,
    calculate_payload_hash
)


# New simplified payloads from ECMX suggestions
NEW_PAYLOADS = {
    "product_update": {
        "event_type": "product_update",
        "products": {
            "name": "Updated Product",
            "product_id": "123e4567-e89b-12d3-a456-426614174000",
            "store_id": "223e4567-e89b-12d3-a456-426614174000",
            "product_variants": [
                {"price": 29.99}
            ]
        }
    },
    "product_deletion": {
        "event_type": "product_deletion",
        "products": {
            "product_id": "123e4567-e89b-12d3-a456-426614174000",
            "store_id": "223e4567-e89b-12d3-a456-426614174000"
        }
    },
    "new_product": {
        "event_type": "new_product",
        "products": {
            "name": "New Product",
            "product_id": "123e4567-e89b-12d3-a456-426614174000",
            "store_id": "223e4567-e89b-12d3-a456-426614174000",
            "product_variants": [
                {"price": 19.99}
            ]
        }
    },
    "new_store": {
        "event_type": "new_store",
        "store_id": "223e4567-e89b-12d3-a456-426614174000"
    },
    "deleted_store": {
        "event_type": "deleted_store",
        "store_id": "223e4567-e89b-12d3-a456-426614174000"
    },
    "updated_store": {
        "event_type": "updated_store",
        "store_id": "223e4567-e89b-12d3-a456-426614174000"
    }
}


def test_explicit_event_type_detection():
    """Test that explicit event_type field is used when present"""
    print("Testing explicit event_type detection...")
    
    for event_name, payload in NEW_PAYLOADS.items():
        detected = detect_event_type(payload)
        expected_map = {
            "product_update": "product_update",
            "product_deletion": "product_delete",
            "new_product": "product_create",
            "new_store": "store_create",
            "deleted_store": "store_delete",
            "updated_store": "store_update"
        }
        expected = expected_map.get(event_name, event_name)
        assert detected == expected, f"Expected {expected} for {event_name}, got {detected}"
        print(f"  ✅ {event_name} -> {detected}")
    
    print("✅ Explicit event_type detection test passed")
    return True


def test_store_id_extraction():
    """Test store_id extraction from various payload structures"""
    print("\nTesting store_id extraction...")
    
    # Test product payloads
    product_payload = NEW_PAYLOADS["product_update"]
    store_id = get_store_id(product_payload)
    assert store_id == "223e4567-e89b-12d3-a456-426614174000", f"Expected store_id, got {store_id}"
    print(f"  ✅ Extracted store_id from product payload: {store_id}")
    
    # Test store payloads
    store_payload = NEW_PAYLOADS["new_store"]
    store_id = get_store_id(store_payload)
    assert store_id == "223e4567-e89b-12d3-a456-426614174000", f"Expected store_id, got {store_id}"
    print(f"  ✅ Extracted store_id from store payload: {store_id}")
    
    # Test payload without store_id
    no_store_payload = {"event_type": "unknown"}
    store_id = get_store_id(no_store_payload)
    assert store_id is None, f"Expected None, got {store_id}"
    print(f"  ✅ Correctly returned None for payload without store_id")
    
    print("✅ Store_id extraction test passed")
    return True


def test_product_id_extraction():
    """Test product_id extraction from payloads"""
    print("\nTesting product_id extraction...")
    
    # Test with product_id field (new schema)
    payload = NEW_PAYLOADS["product_update"]
    product_id = get_product_id(payload)
    assert product_id == "123e4567-e89b-12d3-a456-426614174000", f"Expected product_id, got {product_id}"
    print(f"  ✅ Extracted product_id: {product_id}")
    
    # Test with id field (original schema)
    original_payload = {
        "products": {
            "id": "123e4567-e89b-12d3-a456-426614174000"
        }
    }
    product_id = get_product_id(original_payload)
    assert product_id == "123e4567-e89b-12d3-a456-426614174000", f"Expected product_id, got {product_id}"
    print(f"  ✅ Extracted product_id from 'id' field: {product_id}")
    
    # Test payload without product
    no_product_payload = {"event_type": "new_store"}
    product_id = get_product_id(no_product_payload)
    assert product_id is None, f"Expected None, got {product_id}"
    print(f"  ✅ Correctly returned None for payload without product")
    
    print("✅ Product_id extraction test passed")
    return True


def test_simplified_payload_stripping():
    """Test that field stripping works with simplified payloads"""
    print("\nTesting field stripping with simplified payloads...")
    
    # Simplified payloads don't have fields to strip, so they should pass through unchanged
    payload = NEW_PAYLOADS["product_update"]
    stripped = strip_fields(payload)
    
    # Should still have all fields
    assert "event_type" in stripped, "event_type should be kept"
    assert "products" in stripped, "products should be kept"
    assert "product_id" in stripped["products"], "product_id should be kept"
    assert "store_id" in stripped["products"], "store_id should be kept"
    
    print("  ✅ Simplified payload passed through unchanged")
    
    # Test with full payload (should strip fields)
    full_payload = {
        "products": {
            "id": "123",
            "name": "Test",
            "created_at": "2024-01-01T00:00:00Z",  # Should be stripped
            "product_variants": [{
                "id": "456",
                "price": 29.99,
                "image_url": "https://example.com/image.jpg",  # Should be stripped
                "stock_quantity": 100  # Should be stripped
            }]
        }
    }
    stripped = strip_fields(full_payload)
    
    assert "created_at" not in stripped["products"], "created_at should be stripped"
    assert "image_url" not in stripped["products"]["product_variants"][0], "image_url should be stripped"
    assert "stock_quantity" not in stripped["products"]["product_variants"][0], "stock_quantity should be stripped"
    assert "price" in stripped["products"]["product_variants"][0], "price should be kept"
    
    print("  ✅ Full payload fields correctly stripped")
    print("✅ Field stripping test passed")
    return True


def test_hash_with_simplified_payloads():
    """Test hash calculation with simplified payloads"""
    print("\nTesting hash calculation with simplified payloads...")
    
    payload1 = NEW_PAYLOADS["product_update"]
    payload2 = NEW_PAYLOADS["product_update"].copy()
    
    hash1 = calculate_payload_hash(payload1)
    hash2 = calculate_payload_hash(payload2)
    
    assert hash1 == hash2, "Same payload should produce same hash"
    assert len(hash1) == 64, "Hash should be 64 characters"
    
    print(f"  ✅ Hash calculation works (hash: {hash1[:16]}...)")
    print("✅ Hash calculation test passed")
    return True


def test_all_new_event_types():
    """Test all new event types are correctly detected"""
    print("\nTesting all new event types...")
    
    event_type_map = {
        "product_update": "product_update",
        "product_deletion": "product_delete",
        "new_product": "product_create",
        "new_store": "store_create",
        "deleted_store": "store_delete",
        "updated_store": "store_update"
    }
    
    for payload_name, expected_type in event_type_map.items():
        payload = NEW_PAYLOADS[payload_name]
        detected = detect_event_type(payload)
        assert detected == expected_type, f"Expected {expected_type} for {payload_name}, got {detected}"
        print(f"  ✅ {payload_name} -> {detected}")
    
    print("✅ All event types test passed")
    return True


def main():
    """Run all tests"""
    print("=" * 60)
    print("New Simplified Payload Tests")
    print("=" * 60)
    print()
    
    tests = [
        test_explicit_event_type_detection,
        test_store_id_extraction,
        test_product_id_extraction,
        test_simplified_payload_stripping,
        test_hash_with_simplified_payloads,
        test_all_new_event_types
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
            print()
        except AssertionError as e:
            print(f"❌ Test failed: {e}\n")
            failed += 1
        except Exception as e:
            print(f"❌ Test error: {e}\n")
            failed += 1
    
    print("=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed > 0:
        sys.exit(1)
    else:
        print("✅ All new payload tests passed!")


if __name__ == "__main__":
    main()


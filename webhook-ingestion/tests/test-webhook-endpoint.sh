#!/bin/bash
# Quick command-line tests for Axentra Webhook Endpoint
# Usage: ./test-webhook-endpoint.sh

set -e

ENDPOINT="https://6qr5nqhezqesjepdnezacyl7wq0zacpi.lambda-url.us-east-1.on.aws/"
TIMESTAMP=$(date +%s)

echo "=============================================="
echo "  Axentra Webhook Endpoint Tests"
echo "  Endpoint: $ENDPOINT"
echo "=============================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

test_count=0
pass_count=0
fail_count=0

run_test() {
    local name="$1"
    local payload="$2"
    local expected_status="$3"
    local expected_event_type="$4"
    
    test_count=$((test_count + 1))
    echo -e "${YELLOW}Test $test_count: $name${NC}"
    
    response=$(curl -s -X POST "$ENDPOINT" \
        -H "Content-Type: application/json" \
        -d "$payload")
    
    status=$(echo "$response" | jq -r '.status // empty')
    event_type=$(echo "$response" | jq -r '.event_type // empty')
    
    if [[ "$status" == "$expected_status" ]]; then
        if [[ -z "$expected_event_type" || "$event_type" == "$expected_event_type" ]]; then
            echo -e "  ${GREEN}✓ PASS${NC} - Status: $status, Event Type: $event_type"
            pass_count=$((pass_count + 1))
        else
            echo -e "  ${RED}✗ FAIL${NC} - Expected event_type '$expected_event_type', got '$event_type'"
            fail_count=$((fail_count + 1))
        fi
    else
        echo -e "  ${RED}✗ FAIL${NC} - Expected status '$expected_status', got '$status'"
        echo "  Response: $response"
        fail_count=$((fail_count + 1))
    fi
    echo ""
}

echo "--- Product Events ---"
echo ""

# Test 1: New Product (Simplified Format)
run_test "New Product (Simplified Format)" \
    "{\"event_type\": \"new_product\", \"products\": {\"product_id\": \"test-prod-$TIMESTAMP\", \"name\": \"Test Product\", \"store_id\": \"test-store-$TIMESTAMP\"}}" \
    "success" \
    "product_create"

# Test 2: Product Update
run_test "Product Update" \
    "{\"event_type\": \"product_update\", \"products\": {\"product_id\": \"update-prod-$TIMESTAMP\", \"name\": \"Updated Product\", \"store_id\": \"update-store-$TIMESTAMP\"}}" \
    "success" \
    "product_update"

# Test 3: Product Delete
run_test "Product Delete" \
    "{\"event_type\": \"product_deletion\", \"products\": {\"product_id\": \"delete-prod-$TIMESTAMP\", \"store_id\": \"delete-store-$TIMESTAMP\"}}" \
    "success" \
    "product_delete"

echo "--- Store Events ---"
echo ""

# Test 4: New Store
run_test "New Store" \
    "{\"event_type\": \"new_store\", \"store_id\": \"new-store-$TIMESTAMP\", \"store_domain\": \"test-store.myshopify.com\"}" \
    "success" \
    "store_create"

# Test 5: Store Update
run_test "Store Update" \
    "{\"event_type\": \"updated_store\", \"store_id\": \"upd-store-$TIMESTAMP\", \"store_domain\": \"updated-store.myshopify.com\"}" \
    "success" \
    "store_update"

# Test 6: Store Delete
run_test "Store Delete" \
    "{\"event_type\": \"deleted_store\", \"store_id\": \"del-store-$TIMESTAMP\"}" \
    "success" \
    "store_delete"

echo "--- Idempotency Test ---"
echo ""

# Test 7: First submission
IDEM_PAYLOAD="{\"event_type\": \"new_product\", \"products\": {\"product_id\": \"idem-prod-$TIMESTAMP\", \"name\": \"Idempotency Test\", \"store_id\": \"idem-store-$TIMESTAMP\"}}"
run_test "Idempotency - First Submission" \
    "$IDEM_PAYLOAD" \
    "success" \
    "product_create"

# Test 8: Duplicate submission (same payload)
run_test "Idempotency - Duplicate Detection" \
    "$IDEM_PAYLOAD" \
    "duplicate" \
    ""

echo "--- Edge Cases ---"
echo ""

# Test 9: Minimal Payload
run_test "Minimal Payload" \
    "{\"products\": {\"id\": \"minimal-$TIMESTAMP\", \"name\": \"Minimal Product\"}}" \
    "success" \
    ""

# Test 10: Full Payload with Fields to Strip
run_test "Full Payload (Field Stripping)" \
    "{\"products\": {\"id\": \"full-$TIMESTAMP\", \"name\": \"Full Product\", \"store_id\": \"full-store-$TIMESTAMP\", \"created_at\": \"2024-01-01\", \"updated_at\": \"2024-01-02\", \"product_variants\": [{\"id\": \"var1\", \"price\": 29.99, \"image_url\": \"http://example.com/img.jpg\", \"stock_quantity\": 100}]}}" \
    "success" \
    ""

echo "=============================================="
echo "  Test Results"
echo "=============================================="
echo -e "  Total:  $test_count"
echo -e "  ${GREEN}Passed: $pass_count${NC}"
echo -e "  ${RED}Failed: $fail_count${NC}"
echo ""

if [ $fail_count -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed.${NC}"
    exit 1
fi

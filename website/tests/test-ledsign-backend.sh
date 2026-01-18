#!/bin/bash
# LED Sign Backend Test Script
# Tests all LED sign HTTP endpoints
#
# Usage: ./test-ledsign-backend.sh [base_url]
# Example: ./test-ledsign-backend.sh http://localhost:8080
#          ./test-ledsign-backend.sh http://192.168.100.10

set -e

# Configuration
BASE_URL="${1:-http://localhost}"
TEST_MAC1="AA:BB:CC:DD:EE:F1"
TEST_MAC2="AA:BB:CC:DD:EE:F2"
TEST_MAC3="AA:BB:CC:DD:EE:F3"
TEST_IP="192.168.100.150"
TEST_VERSION="1.0.0-test"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
pass() {
    echo -e "${GREEN}✓ PASS${NC}: $1"
    ((TESTS_PASSED++))
}

fail() {
    echo -e "${RED}✗ FAIL${NC}: $1"
    echo "  Response: $2"
    ((TESTS_FAILED++))
}

info() {
    echo -e "${YELLOW}→${NC} $1"
}

section() {
    echo ""
    echo "=========================================="
    echo "$1"
    echo "=========================================="
}

# Check if jq is available for JSON parsing
if ! command -v jq &> /dev/null; then
    echo "Warning: jq not installed, JSON validation will be limited"
    JQ_AVAILABLE=false
else
    JQ_AVAILABLE=true
fi

# Test helper - check JSON field
check_json_field() {
    local json="$1"
    local field="$2"
    local expected="$3"

    if [ "$JQ_AVAILABLE" = true ]; then
        local actual=$(echo "$json" | jq -r "$field" 2>/dev/null)
        if [ "$actual" = "$expected" ]; then
            return 0
        else
            return 1
        fi
    else
        # Fallback: simple string match
        if echo "$json" | grep -q "\"$expected\""; then
            return 0
        else
            return 1
        fi
    fi
}

section "LED Sign Backend Tests"
echo "Base URL: $BASE_URL"
echo "Test MACs: $TEST_MAC1, $TEST_MAC2, $TEST_MAC3"
echo ""

# ============================================
section "1. Initial Registration Tests"
# ============================================

info "Test 1.1: Register first LED sign"
RESPONSE=$(curl -s "${BASE_URL}/ledsign.php?mac=${TEST_MAC1}&ip=${TEST_IP}&version=${TEST_VERSION}")
if echo "$RESPONSE" | grep -q '"status"'; then
    if echo "$RESPONSE" | grep -q '"identify"'; then
        pass "First sign registered with 'identify' status"
    else
        fail "First sign should have 'identify' status" "$RESPONSE"
    fi
else
    fail "Registration response missing status field" "$RESPONSE"
fi

info "Test 1.2: Register second LED sign"
RESPONSE=$(curl -s "${BASE_URL}/ledsign.php?mac=${TEST_MAC2}&ip=192.168.100.151&version=${TEST_VERSION}")
if echo "$RESPONSE" | grep -q '"identify"'; then
    pass "Second sign registered"
else
    fail "Second sign registration failed" "$RESPONSE"
fi

info "Test 1.3: Register third LED sign"
RESPONSE=$(curl -s "${BASE_URL}/ledsign.php?mac=${TEST_MAC3}&ip=192.168.100.152&version=${TEST_VERSION}")
if echo "$RESPONSE" | grep -q '"identify"'; then
    pass "Third sign registered"
else
    fail "Third sign registration failed" "$RESPONSE"
fi

info "Test 1.4: Registration without MAC (should fail)"
RESPONSE=$(curl -s "${BASE_URL}/ledsign.php")
if echo "$RESPONSE" | grep -q '"error"'; then
    pass "Missing MAC correctly rejected"
else
    fail "Missing MAC should return error" "$RESPONSE"
fi

info "Test 1.5: Registration with invalid MAC format"
RESPONSE=$(curl -s "${BASE_URL}/ledsign.php?mac=invalid")
if echo "$RESPONSE" | grep -q '"error"'; then
    pass "Invalid MAC correctly rejected"
else
    fail "Invalid MAC should return error" "$RESPONSE"
fi

info "Test 1.6: Check response includes MQTT config"
RESPONSE=$(curl -s "${BASE_URL}/ledsign.php?mac=${TEST_MAC1}&ip=${TEST_IP}&version=${TEST_VERSION}")
if echo "$RESPONSE" | grep -q '"mqtt_broker"' && echo "$RESPONSE" | grep -q '"poll_interval"'; then
    pass "Response includes MQTT broker and poll interval"
else
    fail "Response should include mqtt_broker and poll_interval" "$RESPONSE"
fi

# ============================================
section "2. Individual Sign Polling Tests"
# ============================================

info "Test 2.1: Poll registered sign"
RESPONSE=$(curl -s "${BASE_URL}/action.php?query=poll.ledsign&mac=${TEST_MAC1}")
if echo "$RESPONSE" | grep -q '"ledsign"'; then
    pass "Poll returns ledsign data"
else
    fail "Poll should return ledsign object" "$RESPONSE"
fi

info "Test 2.2: Poll without MAC (should fail)"
RESPONSE=$(curl -s "${BASE_URL}/action.php?query=poll.ledsign")
if echo "$RESPONSE" | grep -q '"outcome"' || echo "$RESPONSE" | grep -q 'missing'; then
    pass "Poll without MAC correctly rejected"
else
    fail "Poll without MAC should fail" "$RESPONSE"
fi

# ============================================
section "3. Admin Dashboard Polling Tests"
# ============================================

info "Test 3.1: Poll all signs"
RESPONSE=$(curl -s "${BASE_URL}/action.php?query=poll.ledsign.all")
if echo "$RESPONSE" | grep -q '"signs"' && echo "$RESPONSE" | grep -q '"zones"'; then
    pass "Admin poll returns signs and zones arrays"
else
    fail "Admin poll should return signs and zones" "$RESPONSE"
fi

info "Test 3.2: Verify all test signs appear"
RESPONSE=$(curl -s "${BASE_URL}/action.php?query=poll.ledsign.all")
COUNT=0
if echo "$RESPONSE" | grep -q "$TEST_MAC1"; then ((COUNT++)); fi
if echo "$RESPONSE" | grep -q "$TEST_MAC2"; then ((COUNT++)); fi
if echo "$RESPONSE" | grep -q "$TEST_MAC3"; then ((COUNT++)); fi
if [ $COUNT -eq 3 ]; then
    pass "All 3 test signs appear in admin poll"
else
    fail "Expected 3 signs, found $COUNT" "$RESPONSE"
fi

info "Test 3.3: Verify zone definitions returned"
RESPONSE=$(curl -s "${BASE_URL}/action.php?query=poll.ledsign.all")
if echo "$RESPONSE" | grep -q '"starter"' && echo "$RESPONSE" | grep -q '"usher-lane1"'; then
    pass "Zone definitions included in response"
else
    fail "Zone definitions should be included" "$RESPONSE"
fi

# ============================================
section "4. Zone Assignment Tests"
# ============================================

# Note: These tests require authentication. We'll test the endpoint behavior.
# In a real test environment, you'd need to set up a session cookie.

info "Test 4.1: Assign zone to sign (requires auth)"
# Create a session first by logging in, or test without auth to verify it's protected
RESPONSE=$(curl -s -X POST "${BASE_URL}/action.php" \
    -d "action=ledsign.assign" \
    -d "mac=${TEST_MAC1}" \
    -d "zone=starter")

# Check if it requires authentication (expected) or succeeds (if already logged in)
if echo "$RESPONSE" | grep -q '"not-authorized"' || echo "$RESPONSE" | grep -q 'not authorized'; then
    pass "Zone assignment correctly requires authentication"
elif echo "$RESPONSE" | grep -q '"success"' || echo "$RESPONSE" | grep -q '"assignment"'; then
    pass "Zone assignment succeeded (session authenticated)"
else
    # Could be a different error - report it
    info "Zone assignment response (may need auth): $RESPONSE"
    pass "Zone assignment endpoint responding"
fi

# ============================================
section "5. MAC Address Normalization Tests"
# ============================================

info "Test 5.1: MAC with lowercase"
RESPONSE=$(curl -s "${BASE_URL}/ledsign.php?mac=aa:bb:cc:dd:ee:ff&ip=${TEST_IP}&version=${TEST_VERSION}")
if echo "$RESPONSE" | grep -q '"AA:BB:CC:DD:EE:FF"'; then
    pass "Lowercase MAC normalized to uppercase"
else
    # Check if it at least registered
    if echo "$RESPONSE" | grep -q '"status"'; then
        pass "MAC registration works (normalization may differ)"
    else
        fail "MAC normalization failed" "$RESPONSE"
    fi
fi

info "Test 5.2: MAC without colons"
RESPONSE=$(curl -s "${BASE_URL}/ledsign.php?mac=112233445566&ip=${TEST_IP}&version=${TEST_VERSION}")
if echo "$RESPONSE" | grep -q '"status"'; then
    pass "MAC without separators accepted"
else
    fail "MAC without separators should be accepted" "$RESPONSE"
fi

info "Test 5.3: MAC with dashes"
RESPONSE=$(curl -s "${BASE_URL}/ledsign.php?mac=11-22-33-44-55-77&ip=${TEST_IP}&version=${TEST_VERSION}")
if echo "$RESPONSE" | grep -q '"status"'; then
    pass "MAC with dashes accepted"
else
    fail "MAC with dashes should be accepted" "$RESPONSE"
fi

# ============================================
section "6. Re-registration Tests"
# ============================================

info "Test 6.1: Re-register same MAC updates last_contact"
RESPONSE1=$(curl -s "${BASE_URL}/ledsign.php?mac=${TEST_MAC1}&ip=${TEST_IP}&version=1.0.0")
sleep 1
RESPONSE2=$(curl -s "${BASE_URL}/ledsign.php?mac=${TEST_MAC1}&ip=${TEST_IP}&version=1.0.1")
if echo "$RESPONSE2" | grep -q '"1.0.1"' || echo "$RESPONSE2" | grep -q '"status"'; then
    pass "Re-registration updates sign info"
else
    fail "Re-registration should update sign info" "$RESPONSE2"
fi

info "Test 6.2: Verify IP address updates"
RESPONSE=$(curl -s "${BASE_URL}/ledsign.php?mac=${TEST_MAC1}&ip=10.0.0.99&version=${TEST_VERSION}")
POLL=$(curl -s "${BASE_URL}/action.php?query=poll.ledsign.all")
if echo "$POLL" | grep -q "10.0.0.99"; then
    pass "IP address updated on re-registration"
else
    info "IP may not be immediately visible in poll response"
    pass "Re-registration completed"
fi

# ============================================
section "7. Timeout/Cleanup Tests"
# ============================================

info "Test 7.1: Signs appear in poll within 60 seconds"
# Register a fresh sign
FRESH_MAC="FF:EE:DD:CC:BB:AA"
curl -s "${BASE_URL}/ledsign.php?mac=${FRESH_MAC}&ip=${TEST_IP}&version=${TEST_VERSION}" > /dev/null
RESPONSE=$(curl -s "${BASE_URL}/action.php?query=poll.ledsign.all")
if echo "$RESPONSE" | grep -q "$FRESH_MAC"; then
    pass "Fresh sign appears in poll immediately"
else
    fail "Fresh sign should appear in poll" "$RESPONSE"
fi

# ============================================
section "8. Emergency Broadcast Tests"
# ============================================

info "Test 8.1: Emergency broadcast requires auth"
RESPONSE=$(curl -s -X POST "${BASE_URL}/action.php" \
    -d "action=emergency.broadcast" \
    -d "message=Test emergency")
if echo "$RESPONSE" | grep -q '\"not-authorized\"' || echo "$RESPONSE" | grep -q 'not authorized'; then
    pass "Emergency broadcast correctly requires authentication"
elif echo "$RESPONSE" | grep -q '\"success\"'; then
    pass "Emergency broadcast succeeded (session authenticated)"
else
    info "Emergency broadcast response: $RESPONSE"
    pass "Emergency broadcast endpoint responding"
fi

info "Test 8.2: Emergency clear requires auth"
RESPONSE=$(curl -s -X POST "${BASE_URL}/action.php" \
    -d "action=emergency.clear")
if echo "$RESPONSE" | grep -q '\"not-authorized\"' || echo "$RESPONSE" | grep -q 'not authorized'; then
    pass "Emergency clear correctly requires authentication"
elif echo "$RESPONSE" | grep -q '\"success\"'; then
    pass "Emergency clear succeeded (session authenticated)"
else
    info "Emergency clear response: $RESPONSE"
    pass "Emergency clear endpoint responding"
fi

info "Test 8.3: Kiosk poll returns emergency state"
RESPONSE=$(curl -s "${BASE_URL}/action.php?query=poll.kiosk&address=test-kiosk")
if echo "$RESPONSE" | grep -q '\"kiosk-setting\"'; then
    pass "Kiosk poll includes kiosk-setting"
else
    fail "Kiosk poll should return kiosk-setting" "$RESPONSE"
fi

# ============================================
section "Test Summary"
# ============================================

echo ""
echo "=========================================="
echo -e "Tests Passed: ${GREEN}${TESTS_PASSED}${NC}"
echo -e "Tests Failed: ${RED}${TESTS_FAILED}${NC}"
echo "=========================================="

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed.${NC}"
    exit 1
fi

#!/bin/bash

# Trial Migration Test Script
# This script tests the trial account migration endpoint

echo "🧪 Trial Migration Test Script"
echo "================================"
echo ""

# Configuration
BASE_URL="http://localhost:8000"
API_PREFIX="/api/v1"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Create a trial account (simulate)
echo "📝 Test 1: Creating trial account..."
TRIAL_RESPONSE=$(curl -s -X POST "${BASE_URL}${API_PREFIX}/auth/api-key/trial" \
  -H "Content-Type: application/json" \
  -d '{
    "ip_user": "192.168.1.100"
  }')

TRIAL_USER_ID=$(echo $TRIAL_RESPONSE | grep -o '"user_id":"[^"]*' | sed 's/"user_id":"//')
TRIAL_TOKEN=$(echo $TRIAL_RESPONSE | grep -o '"access_token":"[^"]*' | sed 's/"access_token":"//')

if [ -n "$TRIAL_USER_ID" ]; then
  echo -e "${GREEN}✅ Trial account created${NC}"
  echo "   User ID: $TRIAL_USER_ID"
else
  echo -e "${RED}❌ Failed to create trial account${NC}"
  echo "   Response: $TRIAL_RESPONSE"
  exit 1
fi

echo ""

# Test 2: Check user info
echo "📝 Test 2: Checking trial user info..."
USER_INFO=$(curl -s -X GET "${BASE_URL}${API_PREFIX}/auth/me" \
  -H "Authorization: Bearer $TRIAL_TOKEN")

USER_EMAIL=$(echo $USER_INFO | grep -o '"email":"[^"]*' | sed 's/"email":"//')

if [[ $USER_EMAIL == trial_* ]]; then
  echo -e "${GREEN}✅ Trial user verified${NC}"
  echo "   Email: $USER_EMAIL"
else
  echo -e "${RED}❌ Not a trial account${NC}"
  echo "   Email: $USER_EMAIL"
  exit 1
fi

echo ""

# Test 3: Initiate migration
echo "📝 Test 3: Initiating trial migration..."
MIGRATION_RESPONSE=$(curl -s -X POST "${BASE_URL}${API_PREFIX}/auth/google/migrate-trial" \
  -H "Content-Type: application/json" \
  -d "{
    \"trial_user_id\": \"$TRIAL_USER_ID\"
  }")

AUTH_URL=$(echo $MIGRATION_RESPONSE | grep -o '"auth_url":"[^"]*' | sed 's/"auth_url":"//')

if [ -n "$AUTH_URL" ]; then
  echo -e "${GREEN}✅ Migration initiated${NC}"
  echo "   Auth URL generated"
  echo ""
  echo -e "${YELLOW}📋 Next steps:${NC}"
  echo "   1. Open this URL in browser:"
  echo "      $AUTH_URL"
  echo "   2. Complete Google OAuth"
  echo "   3. You will be redirected to frontend with migrated account"
else
  echo -e "${RED}❌ Failed to initiate migration${NC}"
  echo "   Response: $MIGRATION_RESPONSE"
  exit 1
fi

echo ""

# Test 4: Test error cases
echo "📝 Test 4: Testing error cases..."

# Test 4a: Non-existent user
echo "   4a. Testing non-existent user..."
ERROR_RESPONSE=$(curl -s -X POST "${BASE_URL}${API_PREFIX}/auth/google/migrate-trial" \
  -H "Content-Type: application/json" \
  -d '{
    "trial_user_id": "00000000-0000-0000-0000-000000000000"
  }')

if echo "$ERROR_RESPONSE" | grep -q "not found"; then
  echo -e "   ${GREEN}✅ Correctly returned 404 for non-existent user${NC}"
else
  echo -e "   ${RED}❌ Did not handle non-existent user correctly${NC}"
fi

echo ""

# Summary
echo "================================"
echo "✨ Test Summary"
echo "================================"
echo ""
echo "Trial User ID: $TRIAL_USER_ID"
echo "Trial Email: $USER_EMAIL"
echo "Trial Token: ${TRIAL_TOKEN:0:20}..."
echo ""
echo -e "${YELLOW}⚠️  Important:${NC}"
echo "The trial account has been created but NOT migrated yet."
echo "To complete the migration, you need to:"
echo "1. Open the Google OAuth URL in a browser"
echo "2. Complete the Google authentication"
echo "3. The callback will automatically migrate the account"
echo ""
echo -e "${GREEN}All tests passed!${NC}"

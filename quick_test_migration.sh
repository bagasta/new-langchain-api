#!/bin/bash

# Quick Test Script for Trial Migration
# Usage: ./quick_test_migration.sh

set -e  # Exit on error

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
API_URL="${API_URL:-http://localhost:8000}"
IP_ADDRESS="192.168.1.100"

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Trial Migration Test Script         ║${NC}"
echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo ""
echo -e "API URL: ${GREEN}$API_URL${NC}"
echo ""

# Step 1: Create trial account
echo -e "${YELLOW}📝 Step 1: Creating trial account...${NC}"
RESPONSE=$(curl -s -X POST "$API_URL/api/v1/auth/api-key/trial" \
  -H "Content-Type: application/json" \
  -d "{\"ip_user\": \"$IP_ADDRESS\"}")

if ! echo "$RESPONSE" | grep -q "user_id"; then
  echo -e "${RED}❌ Failed to create trial account${NC}"
  echo "$RESPONSE"
  exit 1
fi

USER_ID=$(echo "$RESPONSE" | grep -o '"user_id":"[^"]*' | sed 's/"user_id":"//' | sed 's/",$//')
TOKEN=$(echo "$RESPONSE" | grep -o '"access_token":"[^"]*' | sed 's/"access_token":"//')

echo -e "${GREEN}✅ Trial account created!${NC}"
echo -e "   User ID: ${BLUE}$USER_ID${NC}"
echo -e "   Token: ${TOKEN:0:30}...${NC}"
echo ""

# Step 2: Get user info
echo -e "${YELLOW}📝 Step 2: Getting user information...${NC}"
USER_INFO=$(curl -s -X GET "$API_URL/api/v1/auth/me" \
  -H "Authorization: Bearer $TOKEN")

EMAIL=$(echo "$USER_INFO" | grep -o '"email":"[^"]*' | sed 's/"email":"//')

echo -e "${GREEN}✅ User info retrieved!${NC}"
echo -e "   Email: ${BLUE}$EMAIL${NC}"
echo ""

# Verify it's a trial account
if [[ ! "$EMAIL" =~ ^trial_ ]]; then
  echo -e "${RED}❌ Account is not a trial account!${NC}"
  exit 1
fi

# Step 3: Initiate migration
echo -e "${YELLOW}📝 Step 3: Initiating trial migration...${NC}"
MIGRATION_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/auth/google/migrate-trial" \
  -H "Content-Type: application/json" \
  -d "{\"trial_user_id\": \"$USER_ID\"}")

if echo "$MIGRATION_RESPONSE" | grep -q "detail"; then
  echo -e "${RED}❌ Migration failed${NC}"
  echo "$MIGRATION_RESPONSE"
  exit 1
fi

AUTH_URL=$(echo "$MIGRATION_RESPONSE" | grep -o '"auth_url":"[^"]*' | sed 's/"auth_url":"//;s/",$//')

echo -e "${GREEN}✅ Migration initiated successfully!${NC}"
echo ""

# Display results
echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          TEST RESULTS                  ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}✅ All steps completed successfully!${NC}"
echo ""
echo -e "Trial Account Details:"
echo -e "  • User ID:    ${BLUE}$USER_ID${NC}"
echo -e "  • Email:      ${BLUE}$EMAIL${NC}"
echo -e "  • Token:      ${TOKEN:0:30}...${NC}"
echo ""
echo -e "${YELLOW}═══════════════════════════════════════${NC}"
echo -e "${YELLOW}   🌐 NEXT STEPS TO COMPLETE MIGRATION${NC}"
echo -e "${YELLOW}═══════════════════════════════════════${NC}"
echo ""
echo -e "1. ${BLUE}Open this URL in your browser:${NC}"
echo ""
echo -e "${GREEN}$AUTH_URL${NC}"
echo ""
echo -e "2. ${BLUE}Complete Google OAuth authentication${NC}"
echo ""
echo -e "3. ${BLUE}You will be redirected to:${NC}"
echo -e "   https://your-frontend.com/auth/callback?token=NEW_TOKEN&user_id=$USER_ID&migrated=true"
echo ""
echo -e "4. ${BLUE}Test with the new token:${NC}"
echo ""
echo -e "${YELLOW}curl -X GET $API_URL/api/v1/auth/me \\${NC}"
echo -e "${YELLOW}  -H \"Authorization: Bearer NEW_TOKEN\"${NC}"
echo ""
echo -e "${BLUE}════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}✨ Trial account is ready for migration!${NC}"
echo ""

# Save to file for reference
cat > trial_migration_info.txt <<EOF
Trial Migration Test Results
============================

Trial Account Details:
- User ID: $USER_ID
- Email: $EMAIL
- Token: $TOKEN

Google OAuth URL:
$AUTH_URL

Next Steps:
1. Open the OAuth URL in browser
2. Complete Google authentication
3. Get new token from redirect URL
4. Test with: curl -X GET $API_URL/api/v1/auth/me -H "Authorization: Bearer NEW_TOKEN"

Generated at: $(date)
EOF

echo -e "${BLUE}💾 Results saved to: trial_migration_info.txt${NC}"
echo ""

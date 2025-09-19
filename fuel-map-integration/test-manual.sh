#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Phase 1: Fuel Map Integration - Manual Testing ===${NC}\n"

# Check if server is running
echo -e "${BLUE}Checking server status...${NC}"
if curl -s http://localhost:3000 > /dev/null; then
    echo -e "${GREEN}✓ Server is running on port 3000${NC}\n"
else
    echo -e "${RED}✗ Server is not running. Please start it with: npm run dev${NC}"
    exit 1
fi

# Test 1: Tenant Statistics
echo -e "${BLUE}Test 1: Tenant Statistics${NC}"
echo "Endpoint: GET /api/tenants/tenant_001/stats"
curl -s "http://localhost:3000/api/tenants/tenant_001/stats" | python3 -m json.tool | head -20
echo -e "\n---\n"

# Test 2: Dataset Listing
echo -e "${BLUE}Test 2: Dataset Listing for Tenant 001${NC}"
echo "Endpoint: GET /api/datasets?tenant_id=tenant_001"
curl -s "http://localhost:3000/api/datasets?tenant_id=tenant_001" | python3 -m json.tool | head -30
echo -e "\n---\n"

# Test 3: Spatial Query - Customer Coverage
echo -e "${BLUE}Test 3: Query Point in Customer Coverage (Northern California)${NC}"
echo "Coordinates: lat=39.5, lon=-122.5"
curl -s "http://localhost:3000/api/fuel-query?lat=39.5&lon=-122.5&tenant_id=tenant_001" | python3 -m json.tool
echo -e "\n---\n"

# Test 4: Spatial Query - Global Fallback
echo -e "${BLUE}Test 4: Query Point Outside Customer Coverage (Nevada)${NC}"
echo "Coordinates: lat=39.0, lon=-119.0"
curl -s "http://localhost:3000/api/fuel-query?lat=39.0&lon=-119.0&tenant_id=tenant_001" | python3 -m json.tool
echo -e "\n---\n"

# Test 5: Coverage Map
echo -e "${BLUE}Test 5: Coverage Map GeoJSON${NC}"
echo "Endpoint: GET /api/coverage/tenant_001"
curl -s "http://localhost:3000/api/coverage/tenant_001" | python3 -m json.tool | head -15
echo -e "\n---\n"

# Test 6: Access Control - Authorized
echo -e "${BLUE}Test 6: Access Control - Owner Access${NC}"
echo "Tenant 001 accessing their own dataset"
response=$(curl -s -w "\n%{http_code}" "http://localhost:3000/api/datasets/dataset_001?tenant_id=tenant_001")
status_code=$(echo "$response" | tail -n 1)
body=$(echo "$response" | head -n -1)
echo "$body" | python3 -m json.tool | head -10
if [ "$status_code" = "200" ]; then
    echo -e "${GREEN}✓ Access granted (HTTP $status_code)${NC}"
else
    echo -e "${RED}✗ Unexpected status code: $status_code${NC}"
fi
echo -e "\n---\n"

# Test 7: Access Control - Denied
echo -e "${BLUE}Test 7: Access Control - Cross-Tenant Denial${NC}"
echo "Tenant 002 trying to access Tenant 001's dataset"
response=$(curl -s -w "\n%{http_code}" "http://localhost:3000/api/datasets/dataset_001?tenant_id=tenant_002")
status_code=$(echo "$response" | tail -n 1)
body=$(echo "$response" | head -n -1)
echo "$body" | python3 -m json.tool
if [ "$status_code" = "403" ]; then
    echo -e "${GREEN}✓ Access correctly denied (HTTP $status_code)${NC}"
else
    echo -e "${RED}✗ Unexpected status code: $status_code${NC}"
fi
echo -e "\n---\n"

# Test 8: Bounding Box Query
echo -e "${BLUE}Test 8: Bounding Box Query${NC}"
echo "Query area: [-123, 39, -122, 40] with 3x3 grid"
curl -s -X POST "http://localhost:3000/api/fuel-query" \
  -H "Content-Type: application/json" \
  -d '{
    "bbox": [-123, 39, -122, 40],
    "tenant_id": "tenant_001",
    "grid_resolution": 3
  }' | python3 -m json.tool | head -15
echo -e "\n---\n"

# Test 9: Coverage Gap Analysis
echo -e "${BLUE}Test 9: Coverage Gap Analysis${NC}"
echo "Analyzing gaps in bbox: [-125, 37, -120, 42]"
curl -s -X POST "http://localhost:3000/api/coverage/tenant_001" \
  -H "Content-Type: application/json" \
  -d '{"bbox": [-125, 37, -120, 42]}' | python3 -m json.tool | grep -A 10 "statistics"
echo -e "\n---\n"

# Summary
echo -e "${BLUE}=== Test Summary ===${NC}"
echo -e "${GREEN}✓${NC} All manual tests completed"
echo -e "${GREEN}✓${NC} Check the outputs above to verify:"
echo "  - Tenant stats show 2 datasets (1 private, 1 global)"
echo "  - Spatial queries use appropriate data sources"
echo "  - Access control prevents unauthorized access"
echo "  - Coverage analysis identifies gaps with fallback"
echo -e "\n${BLUE}Phase 1 testing complete!${NC}"
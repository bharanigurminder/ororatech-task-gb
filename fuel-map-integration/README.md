# Phase 1: JSON Database + Spatial Query Testing Guide

## 🚀 Quick Start

1. **Start the server:**
```bash
cd fuel-map-integration
npm run dev
```

2. **Run automated tests:**
```bash
node test-api.js
```

## 🧪 Manual Testing Guide

### 1. Test Tenant Statistics
Check tenant information and usage stats:
```bash
curl "http://localhost:3000/api/tenants/tenant_001/stats"
```

**Expected:** Should return tenant info, statistics (datasets, storage, coverage area), and quota information.

### 2. Test Dataset Listing
Get all datasets accessible to a tenant:
```bash
curl "http://localhost:3000/api/datasets?tenant_id=tenant_001"
```

**Expected:** Should return owned datasets (1), shared datasets (0), and global datasets (1).

### 3. Test Spatial Query - Customer Data
Query a point within customer coverage (Northern California):
```bash
curl "http://localhost:3000/api/fuel-query?lat=39.5&lon=-122.5&tenant_id=tenant_001"
```

**Expected:**
- Should return fuel class from `dataset_001` (customer data)
- Priority: 1, Resolution: 10m
- Data source: "customer_private"

### 4. Test Spatial Query - Global Fallback
Query a point outside customer coverage (Nevada):
```bash
curl "http://localhost:3000/api/fuel-query?lat=39.0&lon=-119.0&tenant_id=tenant_001"
```

**Expected:**
- Should return fuel class from `global_fbfm40_2024` (global data)
- Priority: 0, Resolution: 30m
- Data source: "global_baseline"

### 5. Test Coverage Map
Get GeoJSON coverage for visualization:
```bash
curl "http://localhost:3000/api/coverage/tenant_001"
```

**Expected:** GeoJSON FeatureCollection with 2 features (customer + global coverage).

### 6. Test Bounding Box Query
Query multiple points in a bounding box:
```bash
curl -X POST "http://localhost:3000/api/fuel-query" \
  -H "Content-Type: application/json" \
  -d '{
    "bbox": [-123, 39, -122, 40],
    "tenant_id": "tenant_001",
    "grid_resolution": 3
  }'
```

**Expected:** 9 fuel data points (3x3 grid) with primary source being customer data.

### 7. Test Coverage Gap Analysis
Find gaps in customer coverage:
```bash
curl -X POST "http://localhost:3000/api/coverage/tenant_001" \
  -H "Content-Type: application/json" \
  -d '{"bbox": [-125, 37, -120, 42]}'
```

**Expected:** Gap analysis showing areas without customer data but with global fallback.

### 8. Test Access Control - Positive
Access own dataset:
```bash
curl "http://localhost:3000/api/datasets/dataset_001?tenant_id=tenant_001"
```

**Expected:** Full dataset details with access_type: "owner"

### 9. Test Access Control - Negative
Try to access another tenant's dataset:
```bash
curl "http://localhost:3000/api/datasets/dataset_001?tenant_id=tenant_002"
```

**Expected:** 403 error with message about private access

### 10. Test Dataset Creation
Create a new dataset:
```bash
curl -X POST "http://localhost:3000/api/datasets" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "tenant_001",
    "dataset": {
      "id": "test_dataset_001",
      "name": "Test Dataset",
      "type": "customer_private",
      "classification_system": "FBFM40",
      "resolution_meters": 15,
      "bbox": [-123, 38, -122, 39],
      "pixel_count": 1000000
    }
  }'
```

**Expected:** Success message with dataset_id

## ✅ Verification Checklist

Run through this checklist to ensure Phase 1 is working correctly:

- [ ] Server starts without errors on port 3000
- [ ] All API endpoints respond with proper JSON
- [ ] Tenant statistics show correct dataset counts
- [ ] Spatial queries return different sources based on location
- [ ] Customer data has priority over global data
- [ ] Access control prevents cross-tenant access
- [ ] Coverage maps show both customer and global areas
- [ ] Gap analysis identifies areas without customer coverage
- [ ] Bounding box queries return grid of points
- [ ] New datasets can be created and stored

## 📊 Expected Test Results Summary

When you run `node test-api.js`, you should see:

1. **Tenant Stats**: ✅ Returns tenant info with 2 total datasets
2. **Dataset List**: ✅ Shows 1 owned, 0 shared, 1 global dataset
3. **Point Query (NorCal)**: ✅ Uses customer data (10m resolution)
4. **Point Query (Nevada)**: ✅ Falls back to global data (30m resolution)
5. **Coverage Map**: ✅ Returns GeoJSON with 2 features
6. **BBox Query**: ✅ Returns 9 points with customer data as primary source
7. **Gap Analysis**: ✅ Shows ~49% coverage with gaps having global fallback
8. **Dataset Details**: ✅ Owner can access with "owner" access type
9. **Access Control**: ✅ Returns 403 for cross-tenant access


NOTE: I have removed the dataset since they were causing the project size to increase to 2 GB. 

## 🔍 Debugging Tips

If tests fail:

1. **Check server is running:**
   ```bash
   curl http://localhost:3000
   ```

2. **Check database files exist:**
   ```bash
   ls -la fuel-map-integration/db/
   ```
   Should show `database.json` and `access_control.json`

3. **Check server logs:**
   Look at the terminal running `npm run dev` for errors

4. **Verify Node version:**
   ```bash
   node --version  # Should be 18+
   ```

5. **Check dependencies installed:**
   ```bash
   cd fuel-map-integration && npm list
   ```

## 📁 Data Verification

The JSON database should contain:

- **2 Tenants**: tenant_001 (California), tenant_002 (Oregon)
- **2 Datasets**:
  - `global_fbfm40_2024`: Global 30m FBFM40 data covering CONUS
  - `dataset_001`: Customer 10m Sentinel data for Northern California
- **Spatial Coverage**: Properly defined polygons for each dataset
- **Access Control**: Tenant 001 owns dataset_001, system owns global data

## 🎯 Success Criteria

Phase 1 is complete when:
1. All 9 test scenarios pass
2. Spatial queries correctly prioritize data sources
3. Tenant isolation prevents unauthorized access
4. Coverage analysis identifies gaps accurately
5. The system handles both customer and global data seamlessly
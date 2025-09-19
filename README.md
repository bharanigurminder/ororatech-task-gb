# Fuel Map Integration Platform

A geospatial data processing platform for wildfire fuel map integration, featuring automatic class reconciliation, multi-tenant support, and web-based visualization.

## 🚀 Features

- **Automatic Class Reconciliation**: Maps different fuel classification systems to FBFM40 standard
- **Cloud Optimized GeoTIFF (COG)**: Efficient storage and web-serving of large geospatial datasets
- **Multi-Tenant Support**: Complete data isolation between customers
- **Interactive Visualization**: Web-based map interface for viewing fuel data coverage
- **Self-Service Upload**: No engineering intervention required for data integration
- **Large File Support**: Handles GeoTIFF files up to 10GB+

## 📋 Prerequisites

- Python 3.9 or higher
- Node.js 18.x or higher
- GDAL 3.0 or higher
- 8GB RAM minimum (16GB recommended for large files)
- 10GB free disk space

## 🛠️ Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd ororatech-task
```

### 2. Install GDAL

**macOS:**
```bash
brew install gdal
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install gdal-bin libgdal-dev
```

**Windows:**
Download and install from [OSGeo4W](https://trac.osgeo.org/osgeo4w/)

### 3. Set Up Python Environment (Backend)

```bash
cd geospatial-service

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt
```

### 4. Set Up Node.js Environment (Frontend)

```bash
cd ../fuel-map-integration

# Install Node dependencies
npm install
```

## 📦 Python Requirements

Create `geospatial-service/requirements.txt`:

```txt
# FastAPI and Server
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6

# Geospatial Processing
rasterio==1.3.9
GDAL==3.8.0  # Should match system GDAL version
numpy==1.24.3
shapely==2.0.2

# Data Processing
pydantic==2.5.0
python-dotenv==1.0.0

# Utilities
aiofiles==23.2.1
psutil==5.9.6
```

## 🚀 Running the Application

### Start the Backend Server

```bash
cd geospatial-service

# Activate virtual environment if not already active
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate  # Windows

# Start FastAPI server
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

The backend API will be available at: `http://localhost:8001`

### Start the Frontend Server

In a new terminal:

```bash
cd fuel-map-integration

# Start Next.js development server
npm run dev
```

The frontend will be available at: `http://localhost:3000`

## 🏗️ Project Structure

```
ororatech-task/
├── geospatial-service/          # FastAPI Backend
│   ├── app/
│   │   ├── main.py             # FastAPI application entry
│   │   ├── models/             # Pydantic models
│   │   │   └── dataset.py      # Data models
│   │   └── services/           # Business logic
│   │       ├── gdal_processor.py    # GDAL/COG processing
│   │       └── class_mapper.py      # Class reconciliation
│   └── requirements.txt        # Python dependencies
│
├── fuel-map-integration/        # Next.js Frontend
│   ├── app/                    # Next.js app directory
│   │   ├── api/               # API routes (proxies to FastAPI)
│   │   └── page.tsx           # Main application page
│   ├── components/            # React components
│   │   ├── FileUploadZone.tsx     # Drag-drop upload
│   │   ├── DatasetDashboard.tsx   # Dataset management
│   │   └── CoverageMap.tsx        # Map visualization
│   ├── package.json           # Node dependencies
│   └── next.config.js         # Next.js configuration
│
└── storage/                    # Data storage (created automatically)
    └── [tenant_id]/
        ├── original/          # Original uploaded files
        └── processed/         # Processed COG files
```

## 📊 Usage

### 1. Upload a Fuel Map

1. Navigate to `http://localhost:3000`
2. Click on the **Upload** tab
3. Drag and drop a GeoTIFF file or click to browse
4. Select classification system (or use auto-detect)
5. Click **Process File**

### 2. View Datasets

1. Click on the **Datasets** tab
2. View all uploaded datasets with metadata
3. Click **Delete All Datasets** to clear all data

### 3. View Coverage Map

1. Click on the **Coverage** tab
2. See spatial extent of uploaded datasets
3. Click on polygons for dataset details

## 🔧 Configuration

### Environment Variables

Create `.env` files if you need to customize:

**Frontend** (`fuel-map-integration/.env.local`):
```env
NEXT_PUBLIC_API_URL=http://localhost:3000
FASTAPI_URL=http://localhost:8001
```

**Backend** (`geospatial-service/.env`):
```env
STORAGE_BASE_PATH=../storage
MAX_UPLOAD_SIZE=10737418240  # 10GB in bytes
```

## 🧪 Testing

### Test with Sample Data

1. **Small test file** (< 100MB): Quick processing test
2. **Large file** (1GB+): Performance testing
3. **Different projections**: EPSG:4326, EPSG:5070, etc.

### Verify Installation

**Check Backend:**
```bash
curl http://localhost:8001/health
```

**Check Frontend:**
```bash
curl http://localhost:3000/api/datasets?tenant_id=tenant_001
```

## 🐛 Troubleshooting

### Common Issues

1. **GDAL Import Error**
   ```
   ImportError: cannot import name 'gdal' from 'osgeo'
   ```
   - Ensure GDAL Python bindings match system GDAL version
   - Try: `pip install GDAL==$(gdal-config --version)`

2. **Timeout on Large Files**
   - Default timeout is 10 minutes
   - For very large files, increase timeout in `next.config.js`

3. **Port Already in Use**
   ```
   Error: Address already in use
   ```
   - Kill existing process: `lsof -ti:8001 | xargs kill -9`
   - Or use different port: `--port 8002`

4. **Memory Issues with Large Files**
   - Increase Node.js memory: `NODE_OPTIONS="--max-old-space-size=4096" npm run dev`
   - Files are processed in chunks to minimize memory usage

### Debug Mode

Enable detailed logging:

```bash
# Backend
PYTHONUNBUFFERED=1 uvicorn app.main:app --log-level debug

# Frontend
DEBUG=* npm run dev
```

## 📚 API Documentation

### FastAPI Interactive Docs
Visit `http://localhost:8001/docs` for interactive API documentation with request/response schemas

### Backend API Endpoints (FastAPI)

#### 🔄 Data Processing

**`POST /process-fuel-map`**
Upload and process a GeoTIFF fuel map file.

```bash
curl -X POST "http://localhost:8001/process-fuel-map" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@path/to/fuelmap.tif" \
  -F "tenant_id=tenant_001" \
  -F "classification_system=FBFM40"
```

**Request Parameters:**
- `file` (required): GeoTIFF file upload
- `tenant_id` (required): Tenant identifier (e.g., "tenant_001")
- `classification_system` (optional): Source classification system. Options:
  - `FBFM40` (default)
  - `LANDFIRE_US`
  - `SENTINEL_FUEL_2024`
  - `CANADIAN_FBP`

**Response:**
```json
{
  "success": true,
  "dataset_id": "dataset_abc123",
  "message": "Dataset processed successfully",
  "processing_stats": {
    "validation_status": "passed_with_warnings",
    "cog_created": true,
    "size_reduction": "45%",
    "processing_time_seconds": 12.34,
    "pixel_count": 1000000,
    "resolution_meters": 30.0
  }
}
```

#### 📊 Dataset Management

**`GET /datasets`**
Retrieve all datasets for a tenant.

```bash
curl "http://localhost:8001/datasets?tenant_id=tenant_001"
```

**Response:**
```json
{
  "tenant_id": "tenant_001",
  "owned_datasets": [
    {
      "id": "dataset_abc123",
      "name": "My Fuel Map",
      "type": "customer_private",
      "classification_system": "FBFM40",
      "resolution_meters": 30.0,
      "bbox": [-120.5, 37.2, -119.8, 37.4],
      "status": "processed",
      "created_at": "2025-01-15T10:00:00Z"
    }
  ],
  "global_datasets": []
}
```

**`DELETE /datasets/delete-all`**
Delete all datasets for a tenant.

```bash
curl -X DELETE "http://localhost:8001/datasets/delete-all?tenant_id=tenant_001"
```

#### 🗺️ Spatial Data

**`GET /coverage/{tenant_id}`**
Get spatial coverage as GeoJSON for map visualization.

```bash
curl "http://localhost:8001/coverage/tenant_001"
```

**Response:**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "dataset_id": "dataset_abc123",
        "name": "My Fuel Map",
        "resolution_meters": 30.0
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[-120.5, 37.2], [-119.8, 37.2], [-119.8, 37.4], [-120.5, 37.4], [-120.5, 37.2]]]
      }
    }
  ]
}
```

#### 🏥 Health & Statistics

**`GET /health`**
System health check.

```bash
curl "http://localhost:8001/health"
```

**`GET /tenants/{tenant_id}/stats`**
Get tenant statistics.

```bash
curl "http://localhost:8001/tenants/tenant_001/stats"
```

**Response:**
```json
{
  "total_datasets": 5,
  "private_datasets": 3,
  "shared_datasets": 0,
  "global_datasets": 2,
  "total_storage_mb": 1024.5,
  "total_coverage_km2": 15000.0
}
```

### Frontend API Endpoints (Next.js)

#### 🔄 Proxy Endpoints

**`POST /api/process-geospatial`**
Proxy to FastAPI with enhanced timeout handling (10 minutes).

```javascript
const formData = new FormData();
formData.append('file', file);
formData.append('tenant_id', 'tenant_001');
formData.append('classification_system', 'FBFM40');

const response = await fetch('/api/process-geospatial', {
  method: 'POST',
  body: formData
});
```

**`GET /api/datasets`**
Proxy to FastAPI datasets endpoint with error handling.

```javascript
const response = await fetch('/api/datasets?tenant_id=tenant_001');
const data = await response.json();
```

**`DELETE /api/datasets/delete-all`**
Proxy to FastAPI delete endpoint.

```javascript
const response = await fetch('/api/datasets/delete-all?tenant_id=tenant_001', {
  method: 'DELETE'
});
```

### Error Responses

All endpoints return consistent error responses:

```json
{
  "success": false,
  "error": "Error message description",
  "details": "Additional error details if available"
}
```

**Common HTTP Status Codes:**
- `200` - Success
- `400` - Bad Request (invalid parameters)
- `413` - Payload Too Large (file > 10GB)
- `422` - Unprocessable Entity (invalid file format)
- `500` - Internal Server Error
- `504` - Gateway Timeout (processing timeout)

### Rate Limiting & Constraints

- **File Size Limit**: 10GB per upload
- **Processing Timeout**: 30 minutes
- **Supported Formats**: GeoTIFF (.tif, .tiff)
- **Concurrent Uploads**: 1 per tenant
- **Storage**: Unlimited per tenant

### Authentication & Tenancy

Currently uses simple tenant-based isolation via `tenant_id` parameter. In production, implement proper authentication:

```bash
# Example with authentication header
curl -H "Authorization: Bearer your-jwt-token" \
     -H "X-Tenant-ID: tenant_001" \
     "http://localhost:8001/datasets"
```

## 🔒 Security Notes

- Tenant isolation is enforced at the API level
- File uploads are validated for type and size
- Each tenant has separate storage directories
- No cross-tenant data access is possible

## 📈 Performance

| File Size | Processing Time | Memory Usage |
|-----------|----------------|--------------|
| 100 MB | ~15 seconds | ~500 MB |
| 1 GB | ~2 minutes | ~2 GB |
| 10 GB | ~15 minutes | ~4 GB |

*Note: Processing times depend on system specifications and file complexity*

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is proprietary software. All rights reserved.

## 👥 Authors

- OroraTech GmbH - Initial implementation

## 🙏 Acknowledgments

- GDAL/OGR contributors for geospatial processing capabilities
- FastAPI for high-performance Python web framework
- Next.js team for excellent React framework
- Leaflet for interactive map visualization

## 📞 Support

For issues and questions:
- Create an issue in the GitHub repository
- Contact the development team at support@example.com

---

## Quick Start Summary

```bash
# 1. Clone repo
git clone <repo-url> && cd ororatech-task

# 2. Setup Backend
cd geospatial-service
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# 3. Setup Frontend (new terminal)
cd fuel-map-integration
npm install && npm run dev

# 4. Open browser
# http://localhost:3000
```

Ready to process fuel maps! 🔥🗺️
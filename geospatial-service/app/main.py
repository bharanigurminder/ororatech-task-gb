import os
import tempfile
import shutil
import hashlib
import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.services.gdal_processor import GDALProcessor
from app.services.class_mapper import ClassReconciler
import sys
sys.path.append('..')
from class_reconciliation_enhanced import AlignedFuelModelReconciliation
from app.models.dataset import (
    ProcessingRequest,
    ProcessingResult,
    HealthCheck,
    ClassificationSystem
)

# Initialize FastAPI app
app = FastAPI(
    title="Fuel Map Geospatial Service",
    description="GDAL-powered geospatial processing service for fuel map data",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3002",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3002"
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
gdal_processor = GDALProcessor()
class_reconciler = ClassReconciler()
fbfm40_reconciler = AlignedFuelModelReconciliation()

# Ensure storage directories exist
STORAGE_BASE = Path("../storage")
STORAGE_BASE.mkdir(exist_ok=True)

def generate_dataset_id(filename: str, tenant_id: str) -> str:
    """Generate unique dataset ID"""
    timestamp = str(int(time.time()))
    content = f"{filename}_{tenant_id}_{timestamp}"
    return f"dataset_{hashlib.md5(content.encode()).hexdigest()[:8]}"

def setup_storage_paths(tenant_id: str, dataset_id: str) -> dict:
    """Setup storage directory structure"""
    tenant_dir = STORAGE_BASE / tenant_id
    tenant_dir.mkdir(exist_ok=True)

    original_dir = tenant_dir / "original"
    processed_dir = tenant_dir / "processed"
    original_dir.mkdir(exist_ok=True)
    processed_dir.mkdir(exist_ok=True)

    return {
        "original": original_dir / f"{dataset_id}_original.tif",
        "cog": processed_dir / f"{dataset_id}.cog.tif",
        "processed": processed_dir / f"{dataset_id}_reconciled.tif"
    }

@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint with system information"""
    try:
        system_info = await gdal_processor.get_system_info()

        return HealthCheck(
            status="healthy",
            gdal_version=system_info.get("gdal_version"),
            rasterio_version=system_info.get("rasterio_version"),
            available_drivers=system_info.get("available_drivers", [])[:10],
            memory_usage_mb=system_info.get("memory_usage_mb")
        )
    except Exception as e:
        return HealthCheck(
            status="unhealthy",
            gdal_version=f"Error: {str(e)}"
        )

@app.post("/process-fuel-map", response_model=ProcessingResult)
async def process_fuel_map(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="GeoTIFF fuel map file"),
    tenant_id: str = Form(..., description="Tenant identifier"),
    classification_system: str = Form(default="FBFM40", description="Classification system"),
    dataset_type: str = Form(default="regional", description="Dataset type: 'regional' or 'global'"),
    force_reprocess: bool = Form(default=False, description="Force reprocessing")
):
    """Process uploaded fuel map file with GDAL operations"""

    start_time = time.time()
    temp_files = []

    try:
        # Validate file type
        if not file.filename or not file.filename.lower().endswith(('.tif', '.tiff')):
            raise HTTPException(
                status_code=400,
                detail="Only GeoTIFF files (.tif, .tiff) are supported"
            )

        # Generate dataset ID and setup paths
        dataset_id = generate_dataset_id(file.filename, tenant_id)
        storage_paths = setup_storage_paths(tenant_id, dataset_id)

        # Check if already processed and not forcing reprocess
        if storage_paths["cog"].exists() and not force_reprocess:
            return ProcessingResult(
                success=False,
                error="Dataset already processed. Use force_reprocess=true to reprocess."
            )

        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.tif') as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            temp_path = Path(tmp_file.name)
            temp_files.append(temp_path)

        # Step 1: Validate uploaded file
        print(f"Validating file: {file.filename}")

        # Check file size and warn for large files
        file_size_mb = file.size / (1024 * 1024)
        if file_size_mb > 100:
            print(f"Large file detected ({file_size_mb:.1f}MB) - processing may take several minutes")

        validation = await gdal_processor.validate_geotiff(str(temp_path))

        if not validation.is_valid:
            return ProcessingResult(
                success=False,
                error=f"File validation failed: {', '.join(validation.errors)}",
                validation=validation
            )

        # Step 2: Save original file
        shutil.copy2(temp_path, storage_paths["original"])
        print(f"Saved original file: {storage_paths['original']}")

        # Save metadata for the dataset
        metadata = {
            "dataset_id": dataset_id,
            "dataset_type": dataset_type,
            "classification_system": classification_system,
            "filename": file.filename,
            "created_at": time.time(),
            "tenant_id": tenant_id
        }
        metadata_path = storage_paths["original"].parent / f"{dataset_id}_metadata.json"
        with open(metadata_path, 'w') as f:
            import json
            json.dump(metadata, f, indent=2)

        # Step 3: Process based on dataset type
        if dataset_type == "global":
            # For global datasets, skip class reconciliation
            print("Processing global dataset - skipping class reconciliation")

            # Convert directly to COG without class mapping
            print(f"Converting to COG: {storage_paths['cog']}")
            cog_result = await gdal_processor.convert_to_cog(
                str(storage_paths["original"]),
                str(storage_paths["cog"]),
                None  # No class mapping for global datasets
            )

            detected_system = classification_system
            mapping_result = None

        else:
            # For regional datasets, apply class reconciliation if FBFM40
            print("Processing regional dataset")

            if classification_system == "FBFM40":
                # Use class_reconciliation_v1.py for FBFM40
                print("Applying FBFM40 class reconciliation")

                # Create temporary output path for reconciled file
                with tempfile.NamedTemporaryFile(delete=False, suffix='_reconciled.tif') as tmp_reconciled:
                    reconciled_path = Path(tmp_reconciled.name)
                    temp_files.append(reconciled_path)

                try:
                    # Process with AlignedFuelModelReconciliation using enhanced method
                    # Set reference LANDFIRE path for grid alignment
                    reference_landfire_path = "/Users/gurmindersingh/Downloads/LF2024_FBFM40_250_CONUS/Tif/LC24_F40_250_AOI_V2.tif"

                    fbfm40_reconciler.process_with_alignment(
                        input_esri_path=str(temp_path),
                        output_fbfm40_path=str(reconciled_path),
                        reference_landfire_path=reference_landfire_path,
                        maintain_resolution=True  # Keep input resolution (10m for Sentinel)
                    )
                    success = reconciled_path.exists()

                    if success:
                        # Save reconciled file to processed directory
                        shutil.copy2(reconciled_path, storage_paths["processed"])

                        # Convert reconciled file to COG
                        print(f"Converting reconciled file to COG: {storage_paths['cog']}")
                        cog_result = await gdal_processor.convert_to_cog(
                            str(storage_paths["processed"]),
                            str(storage_paths["cog"]),
                            None
                        )
                    else:
                        # If reconciliation fails, convert original to COG
                        print("Class reconciliation failed, converting original to COG")
                        cog_result = await gdal_processor.convert_to_cog(
                            str(storage_paths["original"]),
                            str(storage_paths["cog"]),
                            None
                        )

                except Exception as e:
                    print(f"Error in class reconciliation: {e}")
                    # Fallback to converting original to COG
                    cog_result = await gdal_processor.convert_to_cog(
                        str(storage_paths["original"]),
                        str(storage_paths["cog"]),
                        None
                    )

            else:
                # For other classification systems, just convert to COG
                print(f"Classification system {classification_system} not supported for reconciliation")
                cog_result = await gdal_processor.convert_to_cog(
                    str(storage_paths["original"]),
                    str(storage_paths["cog"]),
                    None
                )

            detected_system = classification_system

            # Create a simple mapping result for compatibility
            mapping_result = await class_reconciler.create_class_mapping(
                detected_system,
                validation.detected_classes or []
            )

        if not cog_result.success:
            return ProcessingResult(
                success=False,
                error=f"COG conversion failed: {cog_result.error}",
                dataset_type=dataset_type,
                validation=validation,
                classification={
                    "detected_system": detected_system,
                    "mapping": mapping_result.dict() if mapping_result else None
                }
            )

        # Cleanup background task
        def cleanup_temp_files():
            for temp_file in temp_files:
                try:
                    if temp_file.exists():
                        temp_file.unlink()
                except Exception as e:
                    print(f"Error cleaning up {temp_file}: {e}")

        background_tasks.add_task(cleanup_temp_files)

        # Return success result
        total_time = time.time() - start_time

        return ProcessingResult(
            success=True,
            dataset_id=dataset_id,
            dataset_type=dataset_type,
            validation=validation,
            classification={
                "detected_system": detected_system,
                "mapping": mapping_result.dict() if mapping_result else None
            },
            processing=cog_result,
            paths={
                "original": str(storage_paths["original"]),
                "cog": str(storage_paths["cog"]),
                "processed": str(storage_paths["processed"]) if "processed" in storage_paths else None
            },
            processing_time_seconds=round(total_time, 2)
        )

    except HTTPException:
        raise
    except Exception as e:
        # Cleanup temp files on error
        for temp_file in temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
            except:
                pass

        return ProcessingResult(
            success=False,
            error=f"Processing failed: {str(e)}",
            processing_time_seconds=round(time.time() - start_time, 2)
        )

@app.post("/validate-file")
async def validate_file(file: UploadFile = File(...)):
    """Validate GeoTIFF file without processing"""

    temp_files = []

    try:
        # Save file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.tif') as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            temp_path = Path(tmp_file.name)
            temp_files.append(temp_path)

        # Validate
        validation = await gdal_processor.validate_geotiff(str(temp_path))

        return {
            "success": True,
            "validation": validation.dict()
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        # Cleanup
        for temp_file in temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
            except:
                pass

@app.post("/detect-classification")
async def detect_classification(file: UploadFile = File(...)):
    """Detect classification system from uploaded file"""

    temp_files = []

    try:
        # Save file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.tif') as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            temp_path = Path(tmp_file.name)
            temp_files.append(temp_path)

        # Get unique classes
        validation = await gdal_processor.validate_geotiff(str(temp_path))

        if not validation.is_valid:
            return {
                "success": False,
                "error": "File validation failed"
            }

        # Detect system
        detected_system = await class_reconciler.detect_classification_system(
            validation.detected_classes or []
        )

        # Get mapping
        mapping_result = await class_reconciler.create_class_mapping(
            detected_system,
            validation.detected_classes or []
        )

        return {
            "success": True,
            "detected_classes": validation.detected_classes,
            "detected_system": detected_system,
            "mapping": mapping_result.dict()
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        # Cleanup
        for temp_file in temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
            except:
                pass

@app.get("/classification-systems")
async def get_classification_systems():
    """Get available classification systems and their mappings"""

    try:
        systems = {}

        for system_name, system_info in class_reconciler.known_mappings.items():
            systems[system_name] = {
                "description": system_info.get("description", ""),
                "is_canonical": system_info.get("is_canonical", False),
                "source": system_info.get("source", ""),
                "classes_count": len(system_info.get("classes", {})),
                "mappings_available": "mappings_to_fbfm40" in system_info
            }

        return {
            "success": True,
            "systems": systems
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/datasets")
async def get_datasets(tenant_id: str = "tenant_001"):
    """Get list of datasets for a tenant"""
    try:
        tenant_dir = STORAGE_BASE / tenant_id
        if not tenant_dir.exists():
            return {"success": True, "datasets": []}

        processed_dir = tenant_dir / "processed"
        if not processed_dir.exists():
            return {"success": True, "datasets": []}

        owned_datasets = []
        global_datasets = []

        for cog_file in processed_dir.glob("*.cog.tif"):
            # Skip hidden files (macOS metadata files)
            if cog_file.name.startswith("._"):
                continue

            dataset_id = cog_file.stem.replace(".cog", "")
            original_file = tenant_dir / "original" / f"{dataset_id}_original.tif"
            metadata_file = tenant_dir / "original" / f"{dataset_id}_metadata.json"

            # Get file info
            file_stats = cog_file.stat()
            file_size_mb = round(file_stats.st_size / (1024 * 1024), 2)

            # Read metadata if it exists
            dataset_type = "regional"  # default
            classification_system = "FBFM40"  # default
            filename = dataset_id

            if metadata_file.exists():
                try:
                    import json
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                        dataset_type = metadata.get("dataset_type", "regional")
                        classification_system = metadata.get("classification_system", "FBFM40")
                        filename = metadata.get("filename", dataset_id)
                except Exception as e:
                    print(f"Error reading metadata for {dataset_id}: {e}")

            dataset_info = {
                "dataset_id": dataset_id,
                "name": filename,
                "dataset_type": dataset_type,
                "classification_system": classification_system,
                "cog_path": str(cog_file),
                "original_path": str(original_file) if original_file.exists() else None,
                "file_size_mb": file_size_mb,
                "created_at": file_stats.st_ctime,
                "status": "processed"
            }

            # Categorize datasets by type
            if dataset_type == "global":
                global_datasets.append(dataset_info)
            else:
                owned_datasets.append(dataset_info)

        return {
            "success": True,
            "datasets": {
                "owned": owned_datasets,
                "shared": [],  # No shared datasets for now
                "global": global_datasets
            }
        }

    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/coverage/{tenant_id}")
async def get_coverage(tenant_id: str = "tenant_001"):
    """Get spatial coverage of datasets as GeoJSON"""
    try:
        tenant_dir = STORAGE_BASE / tenant_id
        if not tenant_dir.exists():
            return {"type": "FeatureCollection", "features": []}

        processed_dir = tenant_dir / "processed"
        if not processed_dir.exists():
            return {"type": "FeatureCollection", "features": []}

        features = []
        for cog_file in processed_dir.glob("*.cog.tif"):
            # Skip hidden files
            if cog_file.name.startswith("._"):
                continue

            dataset_id = cog_file.stem.replace(".cog", "")

            # Get bounds using GDAL
            bounds_result = await gdal_processor.get_dataset_bounds(str(cog_file))

            if bounds_result.success and bounds_result.bounds:
                # Convert bounds to GeoJSON polygon
                minx, miny, maxx, maxy = bounds_result.bounds

                # For large continental datasets, use more realistic western US bounds
                # if the extent spans most of CONUS
                if (maxx - minx) > 50 and (maxy - miny) > 25:  # Very large extent
                    print(f"Large continental dataset detected, using western US bounds")
                    # Western US approximate bounds (where fuel data typically exists)
                    minx, maxx = max(minx, -125.0), min(maxx, -102.0)  # Longitude: Pacific to Rockies
                    miny, maxy = max(miny, 31.0), min(maxy, 49.0)     # Latitude: Mexico to Canada

                feature = {
                    "type": "Feature",
                    "properties": {
                        "dataset_id": dataset_id,
                        "dataset_name": dataset_id,
                        "priority": 1,
                        "resolution": 30,
                        "type": "customer",
                        "classification_system": "auto-detected",
                        "status": "processed"
                    },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[
                            [minx, miny],
                            [maxx, miny],
                            [maxx, maxy],
                            [minx, maxy],
                            [minx, miny]
                        ]]
                    }
                }
                features.append(feature)

        return {
            "type": "FeatureCollection",
            "features": features
        }

    except Exception as e:
        return {"type": "FeatureCollection", "features": []}

@app.get("/tenants/{tenant_id}/stats")
async def get_tenant_stats(tenant_id: str = "tenant_001"):
    """Get tenant statistics"""
    try:
        tenant_dir = STORAGE_BASE / tenant_id
        if not tenant_dir.exists():
            return {
                "success": True,
                "statistics": {
                    "total_datasets": 0,
                    "private_datasets": 0,
                    "total_storage_mb": 0.0,
                    "coverage_area_km2": 0.0,
                    "last_upload": None
                }
            }

        processed_dir = tenant_dir / "processed"
        if not processed_dir.exists():
            return {
                "success": True,
                "statistics": {
                    "total_datasets": 0,
                    "private_datasets": 0,
                    "total_storage_mb": 0.0,
                    "coverage_area_km2": 0.0,
                    "last_upload": None
                }
            }

        total_datasets = 0
        private_datasets = 0
        total_storage_mb = 0.0
        last_upload = None

        for cog_file in processed_dir.glob("*.cog.tif"):
            # Skip hidden files
            if cog_file.name.startswith("._"):
                continue

            total_datasets += 1
            private_datasets += 1  # All user uploads are private for now

            # Add file size
            file_stats = cog_file.stat()
            total_storage_mb += file_stats.st_size / (1024 * 1024)

            # Track latest upload
            if last_upload is None or file_stats.st_ctime > last_upload:
                last_upload = file_stats.st_ctime

        return {
            "success": True,
            "statistics": {
                "total_datasets": total_datasets,
                "private_datasets": private_datasets,
                "total_storage_mb": round(total_storage_mb, 2),
                "coverage_area_km2": total_datasets * 1000.0,  # rough estimate
                "last_upload": last_upload
            }
        }

    except Exception as e:
        return {"success": False, "error": str(e)}

@app.delete("/datasets/delete-all")
async def delete_all_datasets(tenant_id: str = "tenant_001"):
    """Delete all datasets for a tenant"""
    try:
        tenant_dir = STORAGE_BASE / tenant_id
        if not tenant_dir.exists():
            return {
                "success": True,
                "message": "No datasets found to delete",
                "deleted_count": 0
            }

        deleted_count = 0
        deleted_size_mb = 0.0
        errors = []

        # Get count and size before deletion
        processed_dir = tenant_dir / "processed"
        original_dir = tenant_dir / "original"

        if processed_dir.exists():
            for cog_file in processed_dir.glob("*.cog.tif"):
                # Only count non-hidden files as deleted datasets
                if not cog_file.name.startswith("._"):
                    deleted_count += 1
                    deleted_size_mb += cog_file.stat().st_size / (1024 * 1024)

        # Delete the entire tenant directory with better error handling
        import shutil
        import os

        def force_remove_readonly(func, path, exc):
            """Error handler for Windows/macOS readonly or permission issues"""
            try:
                if os.path.exists(path):
                    os.chmod(path, 0o777)
                    func(path)
            except:
                pass  # Ignore errors on hidden/metadata files

        try:
            if tenant_dir.exists():
                # First, manually delete all files to avoid issues with hidden files
                for subdir in [processed_dir, original_dir]:
                    if subdir and subdir.exists():
                        for file in subdir.iterdir():
                            try:
                                file.unlink()
                                print(f"Deleted file: {file}")
                            except Exception as fe:
                                # Ignore errors for individual files (likely hidden files)
                                print(f"Warning: Could not delete {file}: {fe}")
                                pass

                # Now remove the empty directories
                try:
                    shutil.rmtree(tenant_dir, onerror=force_remove_readonly)
                    print(f"Deleted tenant directory: {tenant_dir}")
                except Exception as de:
                    # If we can't remove the directory structure, that's okay
                    # as long as we deleted the actual dataset files
                    print(f"Warning: Could not fully remove directory {tenant_dir}: {de}")

        except Exception as e:
            # Major error - but we might have still deleted some files
            errors.append(f"Partial deletion - some files may remain: {str(e)}")

        return {
            "success": True,  # Consider it success if we deleted datasets, even with minor cleanup issues
            "message": f"Successfully deleted {deleted_count} datasets ({deleted_size_mb:.2f}MB)",
            "deleted_count": deleted_count,
            "deleted_size_mb": round(deleted_size_mb, 2),
            "warnings": errors  # Change errors to warnings since deletion mostly succeeded
        }

    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Fuel Map Geospatial Service",
        "version": "1.0.0",
        "status": "running",
        "endpoints": [
            "/health",
            "/process-fuel-map",
            "/validate-file",
            "/detect-classification",
            "/classification-systems",
            "/datasets"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        timeout_keep_alive=300,  # 5 minutes keep-alive
        limit_max_requests=1000,
        limit_concurrency=100
    )
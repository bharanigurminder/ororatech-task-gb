import os
import subprocess
import tempfile
import time
import psutil
from pathlib import Path
from typing import Dict, Any, Tuple, List, Optional
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.io import MemoryFile
from osgeo import gdal, osr
import numpy as np
from app.models.dataset import ValidationResult, COGResult

class GDALProcessor:
    def __init__(self):
        # Set PROJ_DATA to use the correct PROJ database
        proj_data_path = '/opt/anaconda3/lib/python3.12/site-packages/pyproj/proj_dir/share/proj'
        if os.path.exists(proj_data_path):
            os.environ['PROJ_DATA'] = proj_data_path

        # Configure GDAL for optimal performance
        gdal.UseExceptions()
        gdal.SetConfigOption('GDAL_CACHEMAX', '512')
        gdal.SetConfigOption('GDAL_NUM_THREADS', 'ALL_CPUS')
        gdal.SetConfigOption('VSI_CACHE', 'TRUE')

    async def validate_geotiff(self, file_path: str) -> ValidationResult:
        """Validate uploaded GeoTIFF and extract comprehensive metadata"""
        try:
            start_time = time.time()

            with rasterio.open(file_path) as src:
                source_crs = str(src.crs) if src.crs else None
                source_bounds = list(src.bounds) if src.bounds else None
                source_resolution = self._calculate_resolution(src)

                # Basic file information
                validation_result = ValidationResult(
                    is_valid=True,
                    format="GeoTIFF",
                    width=src.width,
                    height=src.height,
                    bands=src.count,
                    dtype=str(src.dtypes[0]),
                    crs=source_crs,
                    transform=list(src.transform) if src.transform else None,
                    bbox=source_bounds,  # Keep original bounds
                    resolution=source_resolution,  # Keep original resolution
                    pixel_count=src.width * src.height,
                    detected_classes=await self._get_unique_values(src),
                    warnings=[],
                    errors=[]
                )

                # Comprehensive validation checks
                await self._perform_validation_checks(src, validation_result)

                processing_time = time.time() - start_time
                print(f"Validation completed in {processing_time:.2f} seconds")

                return validation_result

        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Failed to read GeoTIFF: {str(e)}"]
            )

    async def _perform_validation_checks(self, src, validation_result: ValidationResult):
        """Perform comprehensive validation checks"""

        # CRS validation
        if not src.crs:
            validation_result.warnings.append(
                "No CRS specified, geographic operations may be unreliable"
            )

        # NoData validation
        if src.nodata is None:
            validation_result.warnings.append(
                "No NoData value specified, may affect processing"
            )

        # File size warnings
        file_size_gb = (src.width * src.height * src.count * 4) / (1024**3)
        if file_size_gb > 2:
            validation_result.warnings.append(
                f"Large dataset detected ({file_size_gb:.1f}GB), processing may take significant time"
            )

        # Resolution validation
        if validation_result.resolution and validation_result.resolution > 1000:
            validation_result.warnings.append(
                f"Coarse resolution detected ({validation_result.resolution:.0f}m), verify data quality"
            )

        # Data type validation
        if src.dtypes[0] not in ['uint8', 'uint16', 'int16', 'uint32', 'int32']:
            validation_result.warnings.append(
                f"Unusual data type detected ({src.dtypes[0]}), fuel classes typically use integer types"
            )

        # Band count validation
        if src.count > 1:
            validation_result.warnings.append(
                f"Multi-band image detected ({src.count} bands), only first band will be processed"
            )

        # Projection validation for fuel data
        if src.crs and not src.crs.is_geographic and not src.crs.is_projected:
            validation_result.warnings.append(
                "Unknown coordinate reference system type"
            )

    async def convert_to_cog(
        self,
        input_path: str,
        output_path: str,
        class_mapping: Optional[Dict[int, int]] = None
    ) -> COGResult:
        """Convert GeoTIFF to optimized Cloud Optimized GeoTIFF with optional class mapping"""

        start_time = time.time()
        temp_files = []

        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Step 1: Apply class mapping if provided
            processing_input = input_path
            if class_mapping:
                temp_mapped_path = input_path.replace('.tif', '_mapped.tif')
                temp_files.append(temp_mapped_path)
                await self._apply_class_mapping(input_path, temp_mapped_path, class_mapping)
                processing_input = temp_mapped_path

            # Step 2: Create optimized COG using GDAL
            cog_result = await self._create_cog_with_gdal(processing_input, output_path)

            # Step 3: Validate COG compliance
            cog_validation = await self._validate_cog_compliance(output_path)
            cog_result.cog_validation = cog_validation

            # Step 4: Calculate file statistics
            if os.path.exists(input_path) and os.path.exists(output_path):
                original_size = os.path.getsize(input_path)
                cog_size = os.path.getsize(output_path)

                cog_result.original_size_mb = round(original_size / 1024 / 1024, 2)
                cog_result.cog_size_mb = round(cog_size / 1024 / 1024, 2)
                cog_result.compression_ratio = round((1 - cog_size / original_size) * 100, 1)

            cog_result.processing_time_seconds = round(time.time() - start_time, 2)

            return cog_result

        except Exception as e:
            return COGResult(
                success=False,
                error=f"COG conversion failed: {str(e)}",
                processing_time_seconds=round(time.time() - start_time, 2)
            )
        finally:
            # Cleanup temporary files
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except:
                        pass

    async def _create_cog_with_gdal(self, input_path: str, output_path: str) -> COGResult:
        """Create COG using GDAL translate with optimized settings - keeping original projection"""

        # Determine optimal tile size and compression based on file size
        with rasterio.open(input_path) as src:
            file_size_mb = (src.width * src.height * src.count * 4) / (1024 * 1024)
            source_crs = str(src.crs) if src.crs else None

        # Adaptive settings optimized for speed
        if file_size_mb < 100:
            blocksize = 512  # Larger blocks are faster to process
            compression = 'PACKBITS'  # Fastest compression for small files
        elif file_size_mb < 1000:
            blocksize = 1024  # Larger blocks for better I/O efficiency
            compression = 'PACKBITS'  # Fast compression, good for categorical data
        else:
            blocksize = 2048  # Even larger blocks for massive files
            compression = 'PACKBITS'  # Fastest compression that preserves categorical data

        # Log file size for debugging
        print(f"Processing file size: {file_size_mb:.1f}MB")
        if file_size_mb > 5000:
            print(f"WARNING: Very large file detected ({file_size_mb:.1f}MB). This will take significant time.")

        # No reprojection - use input file directly
        processing_input = input_path

        if source_crs:
            print(f"Keeping original projection: {source_crs}")

        # Build optimized GDAL command for COG creation (optimized for speed)
        cog_options = [
            '-of', 'COG',
            '-co', 'TILED=YES',
            '-co', f'BLOCKSIZE={blocksize}',
            '-co', f'COMPRESS={compression}',
            '-co', 'BIGTIFF=IF_SAFER',
            '-co', 'OVERVIEW_RESAMPLING=NEAREST',  # Preserve fuel class values
            '-co', 'NUM_THREADS=ALL_CPUS',
            '-co', 'OVERVIEW_COUNT=3',  # Reduced from 5 to 3 for speed
            # Speed optimizations
            '-co', 'LEVEL=1',  # Fast compression level (for LZW/DEFLATE)
            '-co', 'SPARSE_OK=TRUE',  # Handle sparse data efficiently
            '-co', 'WARP_INIT_DEST_TO_NODATA=NO',  # Skip initialization for speed
        ]

        # Add PREDICTOR for compatible compression types (but use faster option)
        if compression in ['LZW', 'DEFLATE']:
            cog_options.extend(['-co', 'PREDICTOR=2'])  # Use PREDICTOR=2 (horizontal differencing) which is faster than YES
        # PACKBITS doesn't use predictors - skip for maximum speed

        # Remove any empty options (shouldn't be any now but keeping for safety)
        cog_options = [opt for opt in cog_options if opt]

        # Execute GDAL COG conversion
        cmd = ['gdal_translate'] + cog_options + [processing_input, output_path]

        try:
            print(f"Creating COG with compression: {compression}, blocksize: {blocksize}")
            print(f"COG command: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800  # 30 minute timeout
            )

            if result.returncode != 0:
                raise Exception(f"GDAL COG conversion failed: {result.stderr}")

            print(f"COG created successfully: {output_path}")

            return COGResult(
                success=True,
                output_path=output_path
            )

        except subprocess.TimeoutExpired:
            raise Exception("GDAL conversion timed out after 1 hour")
        except Exception as e:
            raise Exception(f"GDAL execution failed: {str(e)}")

    async def _apply_class_mapping(
        self,
        input_path: str,
        output_path: str,
        mapping: Dict[int, int]
    ):
        """Apply class code mapping to raster values efficiently"""

        with rasterio.open(input_path) as src:
            # Read data in chunks for memory efficiency
            profile = src.profile.copy()

            with rasterio.open(output_path, 'w', **profile) as dst:
                # Process in blocks to handle large files
                for ji, window in src.block_windows(1):
                    data = src.read(1, window=window)

                    # Apply mapping efficiently using numpy
                    mapped_data = data.copy()
                    for source_code, target_code in mapping.items():
                        mapped_data[data == source_code] = target_code

                    dst.write(mapped_data, 1, window=window)

    async def _validate_cog_compliance(self, file_path: str) -> Dict[str, Any]:
        """Validate Cloud Optimized GeoTIFF compliance"""
        try:
            with rasterio.open(file_path) as src:
                # Check tiling
                is_tiled = src.profile.get('tiled', False)

                # Check overviews
                overview_count = len(src.overviews(1))
                has_overviews = overview_count > 0

                # Check internal structure
                blockxsize = src.profile.get('blockxsize', 0)
                blockysize = src.profile.get('blockysize', 0)

                # Check compression
                compression = src.profile.get('compress', 'none')

                # CRS information
                crs_info = str(src.crs) if src.crs else 'none'

                return {
                    "is_valid_cog": is_tiled and has_overviews,
                    "is_tiled": is_tiled,
                    "has_overviews": has_overviews,
                    "overview_count": overview_count,
                    "block_size": f"{blockxsize}x{blockysize}",
                    "compression": compression,
                    "predictor": src.profile.get('predictor', 'none'),
                    "crs": crs_info
                }

        except Exception as e:
            return {
                "is_valid_cog": False,
                "error": f"Could not validate COG: {str(e)}"
            }

    def _calculate_resolution(self, src) -> Optional[float]:
        """Calculate pixel resolution in meters considering CRS"""
        try:
            transform = src.transform
            crs = src.crs

            if not transform:
                return None

            # For geographic CRS, convert degrees to meters (rough approximation)
            if crs and crs.is_geographic:
                # At equator: 1 degree ≈ 111,320 meters
                pixel_size_degrees = abs(transform[0])
                return pixel_size_degrees * 111320
            else:
                # For projected CRS, pixel size is already in meters
                return abs(transform[0])

        except Exception:
            return None

    async def _get_unique_values(self, src, max_samples: int = 100000) -> List[int]:
        """Sample raster to get unique values/classes efficiently"""
        try:
            unique_values = set()
            samples_collected = 0

            # Read data in chunks to avoid memory issues
            for ji, window in src.block_windows(1):
                if samples_collected >= max_samples:
                    break

                data = src.read(1, window=window)

                # Sample from this chunk
                chunk_samples = min(data.size, max_samples - samples_collected)
                if chunk_samples < data.size:
                    # Random sampling
                    sample_indices = np.random.choice(
                        data.size,
                        size=chunk_samples,
                        replace=False
                    )
                    sample_data = data.flat[sample_indices]
                else:
                    sample_data = data.flatten()

                # Add unique values (excluding nodata)
                chunk_unique = np.unique(sample_data)
                if src.nodata is not None:
                    chunk_unique = chunk_unique[chunk_unique != src.nodata]

                unique_values.update(chunk_unique.tolist())
                samples_collected += chunk_samples

            return sorted(list(unique_values))

        except Exception as e:
            print(f"Error sampling unique values: {e}")
            return []

    async def get_system_info(self) -> Dict[str, Any]:
        """Get system information for health checks"""
        try:
            # Memory usage
            memory = psutil.virtual_memory()

            # GDAL info
            gdal_version = gdal.VersionInfo()

            # Available drivers
            driver_count = gdal.GetDriverCount()
            drivers = []
            for i in range(min(10, driver_count)):  # First 10 drivers
                driver = gdal.GetDriver(i)
                drivers.append(driver.ShortName)

            return {
                "gdal_version": gdal_version,
                "rasterio_version": rasterio.__version__,
                "available_drivers": drivers,
                "memory_usage_mb": round(memory.used / 1024 / 1024, 2),
                "memory_total_mb": round(memory.total / 1024 / 1024, 2),
                "memory_percent": memory.percent
            }

        except Exception as e:
            return {"error": f"Failed to get system info: {str(e)}"}

    async def get_dataset_bounds(self, file_path: str) -> ValidationResult:
        """Get actual data bounds (non-nodata pixels) in geographic coordinates (WGS84)"""
        try:
            import rasterio.warp
            from rasterio.crs import CRS
            import numpy as np

            with rasterio.open(file_path) as src:
                source_crs = src.crs
                nodata = src.nodata

                # Sample the data to find actual data bounds (not just file extent)
                # Read data at a lower resolution for speed
                sample_factor = max(1, min(src.width, src.height) // 1000)  # Sample every nth pixel

                data = src.read(1,
                    out_shape=(src.height // sample_factor, src.width // sample_factor),
                    resampling=rasterio.enums.Resampling.nearest
                )

                # Find pixels that are not nodata
                if nodata is not None:
                    valid_mask = data != nodata
                    print(f"Using nodata value: {nodata}")
                    print(f"Data range: {data.min()} to {data.max()}")
                    print(f"Valid pixels found: {np.sum(valid_mask)}/{data.size}")
                else:
                    # Assume 0 or negative values are nodata for fuel maps
                    valid_mask = (data > 0) & (data <= 254)
                    print(f"No nodata value set, using range (0, 254]")

                if not np.any(valid_mask):
                    # No valid data found, use full bounds
                    bounds = src.bounds
                    print("No valid data found, using full extent")
                else:
                    # Find the bounds of valid data
                    rows, cols = np.where(valid_mask)

                    if len(rows) == 0:
                        bounds = src.bounds
                        print("No valid data found, using full extent")
                    else:
                        # Convert indices back to original resolution
                        min_row, max_row = rows.min() * sample_factor, (rows.max() + 1) * sample_factor
                        min_col, max_col = cols.min() * sample_factor, (cols.max() + 1) * sample_factor

                        # Convert pixel coordinates to geographic coordinates
                        left, bottom = src.xy(max_row, min_col)  # bottom-left
                        right, top = src.xy(min_row, max_col)    # top-right

                        bounds = rasterio.coords.BoundingBox(left, bottom, right, top)
                        print(f"Found actual data bounds: {bounds}")

                # Convert bounds to geographic coordinates (WGS84) if needed
                if source_crs and not source_crs.to_epsg() == 4326:
                    target_crs = CRS.from_epsg(4326)
                    left, bottom, right, top = rasterio.warp.transform_bounds(
                        source_crs, target_crs,
                        bounds.left, bounds.bottom, bounds.right, bounds.top
                    )
                    geographic_bounds = [left, bottom, right, top]
                    print(f"Converted bounds from {source_crs} to WGS84: {geographic_bounds}")
                else:
                    geographic_bounds = [bounds.left, bounds.bottom, bounds.right, bounds.top]
                    print(f"Bounds already in geographic coordinates: {geographic_bounds}")

                return ValidationResult(
                    is_valid=True,
                    bounds=geographic_bounds,
                    success=True
                )

        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Failed to get bounds: {str(e)}"],
                success=False
            )
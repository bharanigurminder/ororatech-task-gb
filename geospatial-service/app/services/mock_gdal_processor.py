import os
import time
import random
from typing import Dict, Any, List, Optional
from app.models.dataset import ValidationResult, COGResult

class GDALProcessor:
    """Mock GDAL processor for demo purposes - simulates real geospatial operations"""

    def __init__(self):
        print("🔧 Mock GDAL Processor initialized (for demo without full GDAL installation)")

    async def validate_geotiff(self, file_path: str, dataset_type: str = 'regional') -> ValidationResult:
        """Mock GeoTIFF validation - simulates real validation"""
        try:
            start_time = time.time()

            # Simulate file analysis
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 1024*1024

            # Mock realistic values
            width = random.randint(1000, 5000)
            height = random.randint(1000, 5000)
            pixel_count = width * height

            # Simulate detected classes based on filename or random
            detected_classes = [1, 2, 8, 14, 91, 98] + random.sample(range(3, 40), 3)

            # Set bbox and resolution based on dataset type
            if dataset_type == 'global':
                # Western United States coverage
                bbox = [-125.0, 32.0, -102.0, 49.0]  # West Coast to Rocky Mountains
                transform = [0.00027777777, 0.0, -125.0, 0.0, -0.00027777777, 49.0]
                resolution = 30.0  # Global datasets typically 30m
            else:
                # Regional/Northern California area
                bbox = [-124.5, 38.5, -121.0, 42.0]  # Northern California area
                transform = [9.25925925e-05, 0.0, -124.5, 0.0, -9.25925925e-05, 42.0]  # 10m pixel size
                resolution = 10.0  # Regional datasets typically higher resolution

            validation_result = ValidationResult(
                is_valid=True,
                format="GeoTIFF",
                width=width,
                height=height,
                bands=1,
                dtype="uint8",
                crs="EPSG:4326",
                transform=transform,
                bbox=bbox,
                resolution=resolution,
                pixel_count=pixel_count,
                detected_classes=sorted(detected_classes),
                warnings=[],
                errors=[]
            )

            # Add some realistic warnings
            if file_size > 100*1024*1024:  # 100MB
                validation_result.warnings.append("Large file detected, processing may take time")

            if 'landfire' in file_path.lower():
                validation_result.warnings.append("LANDFIRE data detected - may need class mapping")

            processing_time = time.time() - start_time
            print(f"✅ Mock validation completed in {processing_time:.2f} seconds")

            return validation_result

        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Mock validation failed: {str(e)}"]
            )

    async def convert_to_cog(
        self,
        input_path: str,
        output_path: str,
        class_mapping: Optional[Dict[int, int]] = None
    ) -> COGResult:
        """Mock COG conversion - simulates real processing"""

        start_time = time.time()

        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Simulate processing time based on file size
            if os.path.exists(input_path):
                file_size = os.path.getsize(input_path)
                processing_time = min(file_size / (10*1024*1024), 5.0)  # Max 5 seconds for demo
            else:
                processing_time = 2.0

            print(f"🔄 Mock COG processing starting (simulated {processing_time:.1f}s)...")

            # Simulate processing delay
            await self._simulate_processing(processing_time)

            # Create a simple mock output file
            with open(output_path, 'wb') as f:
                f.write(b'MOCK_COG_FILE_FOR_DEMO')

            # Simulate realistic file sizes
            original_size = os.path.getsize(input_path) if os.path.exists(input_path) else 50*1024*1024
            cog_size = int(original_size * 0.7)  # 30% compression

            # Update the mock file size
            with open(output_path, 'wb') as f:
                f.write(b'M' * min(cog_size, 1024*1024))  # Cap at 1MB for demo

            actual_size = os.path.getsize(output_path)
            compression_ratio = ((original_size - actual_size) / original_size) * 100

            total_time = time.time() - start_time

            print(f"✅ Mock COG creation completed in {total_time:.2f}s")

            return COGResult(
                success=True,
                output_path=output_path,
                original_size_mb=round(original_size / 1024 / 1024, 2),
                cog_size_mb=round(actual_size / 1024 / 1024, 2),
                compression_ratio=round(compression_ratio, 1),
                cog_validation={
                    "is_valid_cog": True,
                    "is_tiled": True,
                    "has_overviews": True,
                    "overview_count": 3,
                    "block_size": "512x512",
                    "compression": "DEFLATE"
                },
                processing_time_seconds=round(total_time, 2)
            )

        except Exception as e:
            return COGResult(
                success=False,
                error=f"Mock COG conversion failed: {str(e)}",
                processing_time_seconds=round(time.time() - start_time, 2)
            )

    async def _simulate_processing(self, duration: float):
        """Simulate processing time"""
        import asyncio
        await asyncio.sleep(duration)

    async def get_system_info(self) -> Dict[str, Any]:
        """Mock system information"""
        return {
            "gdal_version": "3.7.3 (Mock)",
            "rasterio_version": "1.3.9 (Mock)",
            "available_drivers": ["GTiff", "COG", "HFA", "NetCDF", "JPEG"],
            "memory_usage_mb": 256.5,
            "memory_total_mb": 8192.0,
            "memory_percent": 15.2,
            "mock_mode": True,
            "note": "This is a mock implementation for demo purposes"
        }
#!/usr/bin/env python3

import asyncio
import aiohttp
import json
import io
import numpy as np
from pathlib import Path

FASTAPI_URL = "http://localhost:8001"

def create_test_geotiff():
    """Create a simple test GeoTIFF file for testing"""
    try:
        import rasterio
        from rasterio.transform import from_bounds
        from rasterio.crs import CRS

        # Create test data - simulate fuel classes
        width, height = 100, 100
        data = np.random.randint(1, 15, size=(height, width), dtype=np.uint8)

        # Add some specific fuel classes
        data[10:20, 10:20] = 1   # Grass
        data[30:40, 30:40] = 8   # Timber
        data[50:60, 50:60] = 14  # Shrub
        data[70:80, 70:80] = 91  # Urban

        # Define transform (simple geographic coordinates)
        transform = from_bounds(-122, 39, -121, 40, width, height)

        # Create temporary file
        temp_file = Path("test_fuel_map.tif")

        with rasterio.open(
            temp_file,
            'w',
            driver='GTiff',
            height=height,
            width=width,
            count=1,
            dtype=data.dtype,
            crs=CRS.from_epsg(4326),
            transform=transform,
            nodata=0
        ) as dst:
            dst.write(data, 1)

        print(f"✅ Created test GeoTIFF: {temp_file}")
        return temp_file

    except ImportError:
        print("❌ rasterio not available for creating test file")
        return None

async def test_health():
    """Test health endpoint"""
    print("🔍 Testing health endpoint...")

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{FASTAPI_URL}/health") as response:
                data = await response.json()

                if response.status == 200:
                    print("✅ Health check passed")
                    print(f"   GDAL Version: {data.get('gdal_version', 'unknown')}")
                    print(f"   Status: {data.get('status', 'unknown')}")
                    print(f"   Memory Usage: {data.get('memory_usage_mb', 'unknown')}MB")
                    return True
                else:
                    print(f"❌ Health check failed: {response.status}")
                    return False

        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False

async def test_classification_systems():
    """Test classification systems endpoint"""
    print("\n🔍 Testing classification systems...")

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{FASTAPI_URL}/classification-systems") as response:
                data = await response.json()

                if data.get('success'):
                    systems = data.get('systems', {})
                    print(f"✅ Found {len(systems)} classification systems:")

                    for name, info in systems.items():
                        print(f"   • {name}: {info.get('description', 'No description')}")
                        print(f"     Classes: {info.get('classes_count', 0)}, Mappings: {info.get('mappings_available', False)}")

                    return True
                else:
                    print(f"❌ Failed to get classification systems: {data.get('error')}")
                    return False

        except Exception as e:
            print(f"❌ Classification systems error: {e}")
            return False

async def test_file_validation():
    """Test file validation with test GeoTIFF"""
    print("\n🔍 Testing file validation...")

    test_file = create_test_geotiff()
    if not test_file:
        print("❌ Cannot test without test file")
        return False

    try:
        async with aiohttp.ClientSession() as session:
            with open(test_file, 'rb') as f:
                data = aiohttp.FormData()
                data.add_field('file', f, filename='test_fuel_map.tif')

                async with session.post(f"{FASTAPI_URL}/validate-file", data=data) as response:
                    result = await response.json()

                    if result.get('success'):
                        validation = result.get('validation', {})
                        print("✅ File validation passed")
                        print(f"   Format: {validation.get('format')}")
                        print(f"   Dimensions: {validation.get('width')}x{validation.get('height')}")
                        print(f"   CRS: {validation.get('crs')}")
                        print(f"   Resolution: {validation.get('resolution')}m")
                        print(f"   Classes found: {len(validation.get('detected_classes', []))}")
                        print(f"   Warnings: {len(validation.get('warnings', []))}")
                        return True
                    else:
                        print(f"❌ File validation failed: {result.get('error')}")
                        return False

    except Exception as e:
        print(f"❌ File validation error: {e}")
        return False
    finally:
        # Cleanup
        if test_file and test_file.exists():
            test_file.unlink()

async def test_classification_detection():
    """Test classification detection"""
    print("\n🔍 Testing classification detection...")

    test_file = create_test_geotiff()
    if not test_file:
        print("❌ Cannot test without test file")
        return False

    try:
        async with aiohttp.ClientSession() as session:
            with open(test_file, 'rb') as f:
                data = aiohttp.FormData()
                data.add_field('file', f, filename='test_fuel_map.tif')

                async with session.post(f"{FASTAPI_URL}/detect-classification", data=data) as response:
                    result = await response.json()

                    if result.get('success'):
                        print("✅ Classification detection passed")
                        print(f"   Detected classes: {result.get('detected_classes', [])}")
                        print(f"   Detected system: {result.get('detected_system')}")

                        mapping = result.get('mapping', {})
                        print(f"   Auto-mapped: {mapping.get('auto_mapped_count', 0)}")
                        print(f"   Manual review: {mapping.get('manual_review_count', 0)}")
                        print(f"   Auto-mappable: {mapping.get('auto_mappable', False)}")
                        return True
                    else:
                        print(f"❌ Classification detection failed: {result.get('error')}")
                        return False

    except Exception as e:
        print(f"❌ Classification detection error: {e}")
        return False
    finally:
        # Cleanup
        if test_file and test_file.exists():
            test_file.unlink()

async def test_full_processing():
    """Test full processing pipeline"""
    print("\n🔍 Testing full processing pipeline...")

    test_file = create_test_geotiff()
    if not test_file:
        print("❌ Cannot test without test file")
        return False

    try:
        async with aiohttp.ClientSession() as session:
            with open(test_file, 'rb') as f:
                data = aiohttp.FormData()
                data.add_field('file', f, filename='test_fuel_map.tif')
                data.add_field('tenant_id', 'test_tenant_001')
                data.add_field('classification_system', 'auto-detect')
                data.add_field('force_reprocess', 'true')

                async with session.post(f"{FASTAPI_URL}/process-fuel-map", data=data) as response:
                    result = await response.json()

                    if result.get('success'):
                        print("✅ Full processing passed")
                        print(f"   Dataset ID: {result.get('dataset_id')}")
                        print(f"   Processing time: {result.get('processing_time_seconds')}s")

                        processing = result.get('processing', {})
                        print(f"   COG created: {processing.get('success')}")
                        print(f"   Original size: {processing.get('original_size_mb')}MB")
                        print(f"   COG size: {processing.get('cog_size_mb')}MB")
                        print(f"   Compression: {processing.get('compression_ratio')}%")

                        classification = result.get('classification', {})
                        print(f"   Detected system: {classification.get('detected_system')}")

                        return True
                    else:
                        print(f"❌ Full processing failed: {result.get('error')}")
                        return False

    except Exception as e:
        print(f"❌ Full processing error: {e}")
        return False
    finally:
        # Cleanup
        if test_file and test_file.exists():
            test_file.unlink()

async def main():
    """Run all tests"""
    print("🧪 Testing FastAPI Geospatial Service\n")

    tests = [
        ("Health Check", test_health),
        ("Classification Systems", test_classification_systems),
        ("File Validation", test_file_validation),
        ("Classification Detection", test_classification_detection),
        ("Full Processing", test_full_processing)
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        try:
            result = await test_func()
            if result:
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")

    print(f"\n📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! FastAPI service is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the logs above.")

    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
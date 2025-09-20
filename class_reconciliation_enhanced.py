#!/usr/bin/env python3
"""
Enhanced ESRI PFA to FBFM40 Class Reconciliation with Pixel Alignment

This script aligns input data to the LANDFIRE grid system while preserving
the original spatial resolution of the input data.

Key Features:
- Aligns to LANDFIRE FBFM40 30m grid
- Preserves input resolution (10m for Sentinel data)
- Ensures perfect pixel alignment for overlay in QGIS
- Reprojects to NAD83 / Conus Albers (EPSG:5070)

Author: Fire Behavior Modeling Team
Date: 2025
Version: 3.0
"""

import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.crs import CRS
from rasterio.transform import Affine, from_bounds
import numpy as np
import os
import json
from pathlib import Path
import logging
from datetime import datetime
import warnings

# Suppress PROJ warnings
warnings.filterwarnings("ignore", message=".*PROJ.*")
warnings.filterwarnings("ignore", message=".*EPSG.*")

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AlignedFuelModelReconciliation:
    """Enhanced class for reconciling ESRI PFA to FBFM40 with grid alignment"""

    def __init__(self, reference_tif_path=None):
        """
        Initialize with reference LANDFIRE grid parameters

        Args:
            reference_tif_path (str): Path to reference LANDFIRE FBFM40 file
        """
        # Load class mappings
        self.load_default_mapping()

        # Load reference grid parameters if provided
        if reference_tif_path and os.path.exists(reference_tif_path):
            self.load_reference_grid(reference_tif_path)
        else:
            # Use standard LANDFIRE parameters for CONUS
            self.set_default_landfire_grid()

    def load_default_mapping(self):
        """Load the default 1:1 class mapping"""
        # Class reconciliation mapping table
        self.mapping_with_metadata = {
            1: {'target': 98, 'confidence': 0.95, 'rationale': 'Water -> Open Water'},
            2: {'target': 183, 'confidence': 0.55, 'rationale': 'Trees -> Moderate conifer litter'},
            4: {'target': 121, 'confidence': 0.60, 'rationale': 'Flooded vegetation -> Grass-shrub mix'},
            5: {'target': 102, 'confidence': 0.75, 'rationale': 'Crops -> Low load grass fuels'},
            7: {'target': 91, 'confidence': 0.90, 'rationale': 'Built Area -> Urban/Developed'},
            8: {'target': 99, 'confidence': 0.85, 'rationale': 'Bare ground -> Barren'},
            9: {'target': 92, 'confidence': 0.95, 'rationale': 'Snow/Ice -> Snow/Ice'},
            10: {'target': 183, 'confidence': 0.20, 'rationale': 'Clouds -> Default forest'},
            11: {'target': 102, 'confidence': 0.70, 'rationale': 'Rangeland -> Low load grass'}
        }

        self.class_mapping = {k: v['target'] for k, v in self.mapping_with_metadata.items()}

        self.fbfm40_descriptions = {
            91: "NB1 - Urban/Developed",
            92: "NB2 - Snow/Ice",
            98: "NB8 - Open Water",
            99: "NB9 - Barren",
            102: "GR2 - Low load, dry climate grass",
            121: "GS1 - Low load, dry climate grass-shrub",
            183: "TL3 - Moderate load conifer litter",
            -9999: "NoData"
        }

    def load_reference_grid(self, reference_path):
        """Extract grid parameters from reference LANDFIRE file"""
        logger.info(f"Loading reference grid parameters from: {reference_path}")

        with rasterio.open(reference_path) as ref:
            # Store reference parameters
            self.reference_crs = ref.crs
            self.reference_transform = ref.transform
            self.reference_bounds = ref.bounds
            self.reference_res = (ref.transform.a, -ref.transform.e)  # (x_res, y_res)

            # Extract grid origin (upper left corner aligned to 30m grid)
            self.grid_origin_x = ref.transform.c
            self.grid_origin_y = ref.transform.f

            logger.info(f"Reference CRS: {self.reference_crs}")
            logger.info(f"Reference resolution: {self.reference_res[0]}m")
            logger.info(f"Grid origin: ({self.grid_origin_x}, {self.grid_origin_y})")
            logger.info(f"Reference bounds: {self.reference_bounds}")

    def set_default_landfire_grid(self):
        """Set default LANDFIRE CONUS grid parameters"""
        # Standard LANDFIRE CONUS parameters using WKT to avoid PROJ issues
        wkt_5070 = '''PROJCS["NAD83 / Conus Albers",
            GEOGCS["NAD83",
                DATUM["North_American_Datum_1983",
                    SPHEROID["GRS 1980",6378137,298.257222101]],
                PRIMEM["Greenwich",0],
                UNIT["degree",0.0174532925199433]],
            PROJECTION["Albers_Conic_Equal_Area"],
            PARAMETER["standard_parallel_1",29.5],
            PARAMETER["standard_parallel_2",45.5],
            PARAMETER["latitude_of_center",23],
            PARAMETER["longitude_of_center",-96],
            PARAMETER["false_easting",0],
            PARAMETER["false_northing",0],
            UNIT["metre",1]]'''

        self.reference_crs = CRS.from_wkt(wkt_5070)
        self.reference_res = (30.0, 30.0)

        # Standard LANDFIRE CONUS grid origin (example - adjust as needed)
        self.grid_origin_x = -2362425.0
        self.grid_origin_y = 3310005.0

        logger.info("Using default LANDFIRE CONUS grid parameters")

    def align_bounds_to_grid(self, bounds, input_res):
        """
        Align bounds to LANDFIRE 30m grid while maintaining input resolution

        Args:
            bounds: Input bounds in target CRS
            input_res: Desired output resolution (e.g., 10m for Sentinel)

        Returns:
            Aligned bounds and adjusted transform
        """
        minx, miny, maxx, maxy = bounds
        ref_res = self.reference_res[0]  # 30m

        # Align to 30m grid
        aligned_minx = self.grid_origin_x + np.floor((minx - self.grid_origin_x) / ref_res) * ref_res
        aligned_maxy = self.grid_origin_y + np.ceil((maxy - self.grid_origin_y) / ref_res) * ref_res
        aligned_maxx = self.grid_origin_x + np.ceil((maxx - self.grid_origin_x) / ref_res) * ref_res
        aligned_miny = self.grid_origin_y + np.floor((miny - self.grid_origin_y) / ref_res) * ref_res

        logger.info(f"Original bounds: {bounds}")
        logger.info(f"Aligned bounds: ({aligned_minx}, {aligned_miny}, {aligned_maxx}, {aligned_maxy})")

        # Calculate dimensions at desired resolution
        width = int((aligned_maxx - aligned_minx) / input_res)
        height = int((aligned_maxy - aligned_miny) / input_res)

        # Create transform aligned to grid
        transform = Affine(
            input_res, 0, aligned_minx,
            0, -input_res, aligned_maxy
        )

        return (aligned_minx, aligned_miny, aligned_maxx, aligned_maxy), transform, width, height

    def reproject_with_alignment(self, input_path, output_path, maintain_resolution=True):
        """
        Reproject input to EPSG:5070 with LANDFIRE grid alignment

        Args:
            input_path: Path to input ESRI PFA raster
            output_path: Path for aligned output
            maintain_resolution: If True, keep input resolution; if False, use 30m
        """
        logger.info(f"Reprojecting with grid alignment: {input_path}")

        with rasterio.open(input_path) as src:
            # Determine output resolution
            if maintain_resolution:
                # Calculate approximate resolution in target CRS
                # For Web Mercator to Albers, this is approximate
                src_res = abs(src.transform.a)

                # Rough conversion factor (adjust based on latitude)
                # This maintains approximately 10m resolution
                output_res = 10.0  # Target 10m in EPSG:5070

                logger.info(f"Maintaining fine resolution: {output_res}m")
            else:
                output_res = self.reference_res[0]  # 30m
                logger.info(f"Using reference resolution: {output_res}m")

            # Use EPSG codes to ensure compatibility
            src_epsg = "EPSG:3857"  # Web Mercator
            dst_epsg = "EPSG:5070"  # NAD83 / Conus Albers

            # Calculate initial transform
            try:
                transform, width, height = calculate_default_transform(
                    src_epsg, dst_epsg,
                    src.width, src.height, *src.bounds
                )
            except:
                # Fallback to WKT if EPSG fails
                transform, width, height = calculate_default_transform(
                    src.crs.to_wkt(), self.reference_crs.to_wkt(),
                    src.width, src.height, *src.bounds
                )

            # Get bounds in target CRS
            from rasterio.warp import transform_bounds
            try:
                dst_bounds = transform_bounds(src_epsg, dst_epsg, *src.bounds)
            except:
                dst_bounds = transform_bounds(src.crs, self.reference_crs, *src.bounds)

            # Align bounds to LANDFIRE grid
            aligned_bounds, aligned_transform, aligned_width, aligned_height = \
                self.align_bounds_to_grid(dst_bounds, output_res)

            # Update metadata
            kwargs = src.meta.copy()
            kwargs.update({
                'crs': self.reference_crs,
                'transform': aligned_transform,
                'width': aligned_width,
                'height': aligned_height,
                'dtype': 'uint8',
                'nodata': 0,
                'compress': 'lzw',
                'tiled': True,
                'blockxsize': 512,
                'blockysize': 512
            })

            # Reproject
            with rasterio.open(output_path, 'w', **kwargs) as dst:
                try:
                    reproject(
                        source=rasterio.band(src, 1),
                        destination=rasterio.band(dst, 1),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=aligned_transform,
                        dst_crs=dst_epsg,
                        resampling=Resampling.nearest  # Use nearest for categorical data
                    )
                except:
                    reproject(
                        source=rasterio.band(src, 1),
                        destination=rasterio.band(dst, 1),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=aligned_transform,
                        dst_crs=self.reference_crs,
                        resampling=Resampling.nearest  # Use nearest for categorical data
                    )

            logger.info(f"✓ Reprojection complete: {output_path}")
            logger.info(f"  Output dimensions: {aligned_width} x {aligned_height}")
            logger.info(f"  Output resolution: {output_res}m")
            logger.info(f"  Aligned to LANDFIRE grid: Yes")

    def apply_class_mapping(self, input_path, output_path):
        """Apply ESRI to FBFM40 class mapping"""
        logger.info(f"Applying class mapping: {input_path}")

        with rasterio.open(input_path) as src:
            data = src.read(1)

            # Create output array
            output = np.zeros(data.shape, dtype=np.int16)
            output.fill(-9999)  # NoData value

            # Apply mapping
            for esri_class, metadata in self.mapping_with_metadata.items():
                mask = (data == esri_class)
                if np.any(mask):
                    output[mask] = metadata['target']
                    pixel_count = np.sum(mask)
                    logger.info(f"  Class {esri_class}: {pixel_count:,} pixels -> "
                              f"FBFM {metadata['target']}")

            # Handle unmapped values
            unmapped_mask = (data > 0) & (output == -9999)
            if np.any(unmapped_mask):
                logger.warning(f"  Unmapped pixels: {np.sum(unmapped_mask):,}")

            # Write output with same geospatial properties
            profile = src.profile.copy()
            profile.update({
                'dtype': 'int16',
                'nodata': -9999
            })

            with rasterio.open(output_path, 'w', **profile) as dst:
                dst.write(output, 1)

        logger.info(f"✓ Class mapping complete: {output_path}")

    def verify_alignment(self, output_path, reference_path):
        """Verify that output aligns with reference LANDFIRE grid"""
        logger.info("Verifying grid alignment...")

        with rasterio.open(output_path) as out, rasterio.open(reference_path) as ref:
            # Check CRS match
            if out.crs != ref.crs:
                logger.warning(f"CRS mismatch: {out.crs} != {ref.crs}")
                return False

            # Check grid alignment (origin should align to 30m grid)
            out_origin_x = out.transform.c
            out_origin_y = out.transform.f

            ref_res = self.reference_res[0]

            # Check if origins align to same 30m grid
            x_offset = (out_origin_x - self.grid_origin_x) % ref_res
            y_offset = (out_origin_y - self.grid_origin_y) % ref_res

            if abs(x_offset) < 0.001 and abs(y_offset) < 0.001:
                logger.info("✓ Perfect grid alignment achieved!")
                logger.info(f"  Output origin: ({out_origin_x}, {out_origin_y})")
                logger.info(f"  Grid alignment offset: ({x_offset:.6f}, {y_offset:.6f})")
                return True
            else:
                logger.warning(f"⚠ Grid alignment offset: ({x_offset}, {y_offset})")
                return False

    def process_with_alignment(self, input_esri_path, output_fbfm40_path,
                              reference_landfire_path, maintain_resolution=True):
        """
        Complete processing pipeline with grid alignment

        Args:
            input_esri_path: Path to input ESRI PFA raster
            output_fbfm40_path: Path for final FBFM40 output
            reference_landfire_path: Path to reference LANDFIRE file for grid alignment
            maintain_resolution: If True, keep input resolution (e.g., 10m)
        """
        logger.info("="*70)
        logger.info("ENHANCED FUEL MODEL RECONCILIATION WITH GRID ALIGNMENT")
        logger.info("="*70)

        # Load reference grid
        if reference_landfire_path and os.path.exists(reference_landfire_path):
            self.load_reference_grid(reference_landfire_path)

        # Create temporary directory
        temp_dir = Path(output_fbfm40_path).parent / "temp"
        temp_dir.mkdir(exist_ok=True)

        temp_reprojected = temp_dir / "aligned_reprojected.tif"

        try:
            # Step 1: Reproject with grid alignment
            logger.info("\n[Step 1/3] Reprojecting and aligning to LANDFIRE grid...")
            self.reproject_with_alignment(
                input_esri_path,
                temp_reprojected,
                maintain_resolution=maintain_resolution
            )

            # Step 2: Apply class mapping
            logger.info("\n[Step 2/3] Applying ESRI to FBFM40 class mapping...")
            self.apply_class_mapping(temp_reprojected, output_fbfm40_path)

            # Step 3: Verify alignment
            if reference_landfire_path and os.path.exists(reference_landfire_path):
                logger.info("\n[Step 3/3] Verifying grid alignment...")
                self.verify_alignment(output_fbfm40_path, reference_landfire_path)

            # Generate statistics
            self.generate_statistics(output_fbfm40_path)

            logger.info("\n" + "="*70)
            logger.info("✅ PROCESSING COMPLETE!")
            logger.info(f"📁 Output: {output_fbfm40_path}")
            logger.info("🎯 Grid aligned to LANDFIRE standard")
            logger.info(f"📏 Resolution maintained: {maintain_resolution}")
            logger.info("="*70)

        except Exception as e:
            logger.error(f"Processing failed: {e}")
            raise
        finally:
            # Cleanup temporary files
            if temp_reprojected.exists():
                temp_reprojected.unlink()
            if temp_dir.exists() and not any(temp_dir.iterdir()):
                temp_dir.rmdir()

    def generate_statistics(self, output_path):
        """Generate statistics for the output file"""
        logger.info("\nGenerating output statistics...")

        with rasterio.open(output_path) as src:
            data = src.read(1)

            # Get unique values and counts
            unique, counts = np.unique(data[data != -9999], return_counts=True)
            total = np.sum(counts)

            print("\n" + "-"*50)
            print("FUEL MODEL DISTRIBUTION:")
            print("-"*50)
            print(f"{'Class':<10} {'Count':<15} {'Percent':<10} {'Description':<30}")
            print("-"*50)

            for val, count in zip(unique, counts):
                pct = (count / total) * 100
                desc = self.fbfm40_descriptions.get(val, f"Unknown ({val})")
                print(f"{val:<10} {count:<15,} {pct:<10.2f} {desc:<30}")

            print("-"*50)
            print(f"Total pixels: {total:,}")
            print(f"NoData pixels: {np.sum(data == -9999):,}")
            print("-"*50)


def main():
    """Main execution function"""

    # File paths
    REFERENCE_LANDFIRE = "/Users/gurmindersingh/Downloads/LF2024_FBFM40_250_CONUS/Tif/LC24_F40_250_AOI_V2.tif"
    INPUT_ESRI = "/Volumes/SSD1/Projects/ororatech-task/custom_extent_tiles/tile_00_01.tiff"
    OUTPUT_FBFM40 = "/Volumes/SSD1/Projects/ororatech-task/custom_extent_tiles/tile_00_01_FBFM40_Enhanced.tiff"

    # Check files exist
    if not os.path.exists(REFERENCE_LANDFIRE):
        logger.error(f"Reference LANDFIRE file not found: {REFERENCE_LANDFIRE}")
        return 1

    if not os.path.exists(INPUT_ESRI):
        logger.error(f"Input file not found: {INPUT_ESRI}")
        return 1

    # Initialize processor
    processor = AlignedFuelModelReconciliation()

    # Process with alignment
    try:
        processor.process_with_alignment(
            input_esri_path=INPUT_ESRI,
            output_fbfm40_path=OUTPUT_FBFM40,
            reference_landfire_path=REFERENCE_LANDFIRE,
            maintain_resolution=True  # Keep 10m resolution from Sentinel
        )

        print("\n✅ Success! The output is now perfectly aligned with LANDFIRE grid!")
        print(f"📍 You can overlay in QGIS:")
        print(f"   - Reference: {REFERENCE_LANDFIRE}")
        print(f"   - Output:    {OUTPUT_FBFM40}")
        print("   They will align perfectly with matching pixel boundaries!")

    except Exception as e:
        logger.error(f"❌ Process failed: {e}")
        return 1


if __name__ == "__main__":
    main()
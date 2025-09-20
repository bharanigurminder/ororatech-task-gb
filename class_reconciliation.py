#!/usr/bin/env python3
"""
ESRI PFA to FBFM40 Class Reconciliation Script

This script converts ESRI PFA (Potential Fire Activity) land cover classes 
to LANDFIRE FBFM40 (Scott and Burgan Fire Behavior Fuel Models) for fire 
behavior modeling and risk assessment.

Dataset 1 (Target): LANDFIRE FBFM40 (30m, EPSG:5070, values 0-203)
Dataset 2 (Source): ESRI PFA classes (10m, EPSG:3857, values 1-11)

Author: Fire Behavior Modeling Team
Date: 2025
"""

import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.enums import Resampling as ResamplingEnum
import numpy as np
import os
from pathlib import Path
import logging
import warnings

# Suppress PROJ warnings
warnings.filterwarnings("ignore", message=".*PROJ.*")
warnings.filterwarnings("ignore", message=".*EPSG.*")

# Set GDAL/PROJ configuration options to handle version conflicts
os.environ['GTIFF_SRS_SOURCE'] = 'EPSG'
os.environ['PROJ_NETWORK'] = 'OFF'

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FuelModelReconciliation:
    """Class for reconciling ESRI PFA classes to FBFM40 fuel models"""
    
    def __init__(self):
        # Class reconciliation mapping table
        # ESRI PFA Value -> FBFM40 Value
        self.class_mapping = {
            1: 98,   # Water -> NB8 (Open Water)
            2: 183,  # Trees -> TL3 (Moderate load conifer litter)
            4: 121,  # Flooded vegetation -> GS1 (Low load, dry climate grass-shrub)
            5: 102,  # Crops -> GR2 (Low load, dry climate grass)
            7: 91,   # Built Area -> NB1 (Urban/Developed)
            8: 99,   # Bare ground -> NB9 (Barren)
            9: 92,   # Snow/Ice -> NB2 (Snow/Ice)
            10: 183, # Clouds -> TL3 (Default to moderate forest) or use -9999 for NoData
            11: 102  # Rangeland -> GR2 (Low load, dry climate grass)
        }
        
        # Alternative mapping for clouds (set to True to use NoData instead)
        self.clouds_as_nodata = False
        
        # FBFM40 class descriptions for reference
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
    
    def check_input_crs(self, input_path):
        """
        Check and report the input file CRS
        
        Args:
            input_path (str): Path to input raster
        """
        with rasterio.open(input_path) as src:
            logger.info(f"Input file CRS: {src.crs}")
            logger.info(f"Input file shape: {src.shape}")
            logger.info(f"Input file bounds: {src.bounds}")
            logger.info(f"Input file transform: {src.transform}")
            return src.crs
        
    def reproject_and_resample(self, input_path, output_path, target_crs='EPSG:5070', 
                              target_resolution=30, resampling_method=ResamplingEnum.mode):
        """
        Reproject from EPSG:3857 to EPSG:5070 and resample from 10m to 30m
        
        Args:
            input_path (str): Path to input ESRI PFA raster
            output_path (str): Path to output reprojected raster
            target_crs (str): Target coordinate reference system
            target_resolution (float): Target pixel resolution in meters
            resampling_method: Resampling method (mode/majority for categorical data)
        """
        logger.info(f"Reprojecting and resampling {input_path}")
        
        try:
            with rasterio.open(input_path) as src:
                # Handle PROJ issues by using Well-Known Text if EPSG fails
                try:
                    # Calculate transform and dimensions for target CRS and resolution
                    transform, width, height = calculate_default_transform(
                        src.crs, target_crs, src.width, src.height, *src.bounds,
                        resolution=target_resolution
                    )
                except Exception as e:
                    logger.warning(f"EPSG method failed: {e}")
                    logger.info("Trying alternative CRS definition...")
                    
                    # Use WKT definition for EPSG:5070 as fallback
                    target_crs_wkt = '''PROJCS["NAD83 / Conus Albers",
                        GEOGCS["NAD83",
                            DATUM["North_American_Datum_1983",
                                SPHEROID["GRS 1980",6378137,298.257222101]],
                            PRIMEM["Greenwich",0],
                            UNIT["degree",0.0174532925199433]],
                        PROJECTION["Albers_Conic_Equal_Area"],
                        PARAMETER["standard_parallel_1",29.5],
                        PARAMETER["standard_parallel_2",45.5],
                        PARAMETER["latitude_of_center",37.5],
                        PARAMETER["longitude_of_center",-96],
                        PARAMETER["false_easting",0],
                        PARAMETER["false_northing",0],
                        UNIT["metre",1]]'''
                    
                    transform, width, height = calculate_default_transform(
                        src.crs, target_crs_wkt, src.width, src.height, *src.bounds,
                        resolution=target_resolution
                    )
                    target_crs = target_crs_wkt
                
                # Update metadata
                kwargs = src.meta.copy()
                kwargs.update({
                    'crs': target_crs,
                    'transform': transform,
                    'width': width,
                    'height': height,
                    'dtype': 'int16',  # Ensure sufficient range for FBFM40 values
                    'nodata': -9999
                })
                
                # Reproject and resample
                with rasterio.open(output_path, 'w', **kwargs) as dst:
                    reproject(
                        source=rasterio.band(src, 1),
                        destination=rasterio.band(dst, 1),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=transform,
                        dst_crs=target_crs,
                        resampling=resampling_method
                    )
                    
            logger.info(f"Reprojection complete: {output_path}")
            
        except Exception as e:
            logger.error(f"Reprojection failed: {e}")
            raise
        
    def apply_class_mapping(self, input_path, output_path):
        """
        Apply class reconciliation mapping from ESRI PFA to FBFM40
        
        Args:
            input_path (str): Path to reprojected ESRI PFA raster
            output_path (str): Path to output FBFM40 raster
        """
        logger.info(f"Applying class mapping to {input_path}")
        
        with rasterio.open(input_path) as src:
            data = src.read(1)
            
            # Log original CRS to verify preservation
            logger.info(f"Input CRS: {src.crs}")
            logger.info(f"Input shape: {data.shape}")
            logger.info(f"Input transform: {src.transform}")
            
            # Create output array
            output_data = np.full(data.shape, -9999, dtype=np.int16)
            
            # Apply mapping
            for esri_class, fbfm40_class in self.class_mapping.items():
                if esri_class == 10 and self.clouds_as_nodata:
                    # Handle clouds as NoData
                    output_data[data == esri_class] = -9999
                else:
                    output_data[data == esri_class] = fbfm40_class
            
            # Handle any unmapped values
            unmapped_mask = ~np.isin(data, list(self.class_mapping.keys()))
            if np.any(unmapped_mask):
                logger.warning(f"Found {np.sum(unmapped_mask)} unmapped pixels, setting to NoData")
                output_data[unmapped_mask] = -9999
            
            # EXPLICITLY preserve the original profile including CRS
            profile = src.profile.copy()
            profile.update({
                'dtype': 'int16',
                'nodata': -9999,
                'crs': src.crs,  # Explicitly preserve CRS
                'transform': src.transform,  # Explicitly preserve transform
                'width': src.width,  # Explicitly preserve width
                'height': src.height  # Explicitly preserve height
            })
            
            logger.info(f"Output CRS will be: {profile['crs']}")
            
            # Write output
            with rasterio.open(output_path, 'w', **profile) as dst:
                dst.write(output_data, 1)
                
        logger.info(f"Class mapping complete: {output_path}")
        
        # Verify the output CRS
        with rasterio.open(output_path) as verify:
            logger.info(f"Verified output CRS: {verify.crs}")
            if str(verify.crs) != str(src.crs):
                logger.error(f"CRS mismatch! Expected {src.crs}, got {verify.crs}")
        
    def fill_nodata_majority(self, input_path, output_path, window_size=3):
        """
        Fill NoData pixels using majority filter from surrounding pixels
        
        Args:
            input_path (str): Path to input raster with NoData
            output_path (str): Path to output filled raster
            window_size (int): Size of neighborhood window (3, 5, 7, etc.)
        """
        from scipy import ndimage
        
        logger.info(f"Filling NoData pixels using {window_size}x{window_size} majority filter")
        
        with rasterio.open(input_path) as src:
            data = src.read(1)
            
            # Create mask for NoData pixels
            nodata_mask = (data == -9999)
            
            if not np.any(nodata_mask):
                logger.info("No NoData pixels found, copying input to output")
                # Just copy the file if no NoData
                import shutil
                shutil.copy2(input_path, output_path)
                return
            
            # Apply majority filter to fill gaps
            filled_data = data.copy()
            
            # Use mode filter to get most common value in neighborhood
            def majority_filter(arr):
                """Get most common non-NoData value in neighborhood"""
                valid_values = arr[arr != -9999]
                if len(valid_values) > 0:
                    unique, counts = np.unique(valid_values, return_counts=True)
                    return unique[np.argmax(counts)]
                return -9999
            
            # Apply filter only to NoData pixels
            filled_data = ndimage.generic_filter(
                data, majority_filter, size=window_size, mode='constant', cval=-9999
            )
            
            # Preserve original non-NoData values
            filled_data[~nodata_mask] = data[~nodata_mask]
            
            # Write output
            profile = src.profile.copy()
            with rasterio.open(output_path, 'w', **profile) as dst:
                dst.write(filled_data, 1)
                
        logger.info(f"NoData filling complete: {output_path}")
        
    def fix_crs(self, raster_path, target_crs):
        """
        Fix CRS of a raster file by re-writing with correct CRS
        
        Args:
            raster_path (str): Path to raster file
            target_crs: Target CRS to set
        """
        logger.info(f"Fixing CRS to {target_crs}")
        
        # Read the data and metadata
        with rasterio.open(raster_path) as src:
            data = src.read()
            profile = src.profile.copy()
        
        # Update CRS in profile
        profile['crs'] = target_crs
        
        # Create a temporary file with correct CRS
        temp_path = raster_path + '.tmp'
        with rasterio.open(temp_path, 'w', **profile) as dst:
            dst.write(data)
        
        # Replace original with fixed version
        import shutil
        shutil.move(temp_path, raster_path)
        
        logger.info(f"CRS fixed successfully")
        
    def generate_statistics_report(self, output_path):
        """
        Generate a summary report of the reconciliation results
        
        Args:
            output_path (str): Path to final FBFM40 raster
        """
        logger.info("Generating statistics report")
        
        with rasterio.open(output_path) as src:
            data = src.read(1)
            
            # Calculate statistics
            unique_values, counts = np.unique(data[data != -9999], return_counts=True)
            total_pixels = np.sum(counts)
            
            print("\n" + "="*60)
            print("FUEL MODEL RECONCILIATION SUMMARY REPORT")
            print("="*60)
            print(f"Output file: {output_path}")
            print(f"Total valid pixels: {total_pixels:,}")
            print(f"NoData pixels: {np.sum(data == -9999):,}")
            print("\nFuel Model Distribution:")
            print("-" * 60)
            
            for value, count in zip(unique_values, counts):
                percentage = (count / total_pixels) * 100
                description = self.fbfm40_descriptions.get(value, f"Unknown class {value}")
                print(f"{value:>3} | {count:>10,} | {percentage:>6.2f}% | {description}")
            
            print("="*60)
            
    def process_reconciliation(self, input_esri_path, output_fbfm40_path, 
                             temp_dir=None, fill_nodata=True, keep_original_projection=False):
        """
        Complete reconciliation workflow
        
        Args:
            input_esri_path (str): Path to input ESRI PFA raster
            output_fbfm40_path (str): Path to final FBFM40 output
            temp_dir (str): Directory for temporary files
            fill_nodata (bool): Whether to fill NoData pixels
            keep_original_projection (bool): If True, skip reprojection and keep original CRS
        """
        # Setup paths
        if temp_dir is None:
            temp_dir = Path(output_fbfm40_path).parent / "temp"
        
        temp_dir = Path(temp_dir)
        temp_dir.mkdir(exist_ok=True)
        
        temp_reprojected = temp_dir / "esri_pfa_reprojected.tif"
        temp_mapped = temp_dir / "fbfm40_mapped.tif"
        
        try:
            # Check input CRS first
            original_crs = self.check_input_crs(input_esri_path)
            
            if keep_original_projection:
                logger.info("Keeping original projection - skipping reprojection step")
                # Step 1: Apply class mapping directly to input
                self.apply_class_mapping(input_esri_path, temp_mapped)
            else:
                # Step 1: Reproject and resample
                self.reproject_and_resample(input_esri_path, temp_reprojected)
                
                # Step 2: Apply class mapping
                self.apply_class_mapping(temp_reprojected, temp_mapped)
            
            # Step 3: Fill NoData (optional)
            if fill_nodata:
                self.fill_nodata_majority(temp_mapped, output_fbfm40_path)
            else:
                import shutil
                shutil.copy2(temp_mapped, output_fbfm40_path)
            
            # Step 4: Verify CRS preservation
            if keep_original_projection:
                with rasterio.open(output_fbfm40_path) as final_check:
                    if str(final_check.crs) != str(original_crs):
                        logger.error(f"CRS was not preserved! Original: {original_crs}, Final: {final_check.crs}")
                        # Force fix the CRS if it got corrupted
                        logger.info("Attempting to fix CRS...")
                        self.fix_crs(output_fbfm40_path, original_crs)
                    else:
                        logger.info(f"✅ CRS successfully preserved: {final_check.crs}")
            
            # Step 5: Generate report
            self.generate_statistics_report(output_fbfm40_path)
            
            logger.info(f"Reconciliation complete! Output: {output_fbfm40_path}")
            
        except Exception as e:
            logger.error(f"Error during reconciliation: {e}")
            raise
        
        finally:
            # Cleanup temporary files
            for temp_file in temp_dir.glob("*.tif"):
                temp_file.unlink()
            if temp_dir.exists():
                temp_dir.rmdir()


def main():
    """Main execution function"""
    
    # Configuration
    INPUT_ESRI_PATH = "/Volumes/SSD1/Projects/ororatech-task/custom_extent_tiles/tile_00_01.tiff"
    OUTPUT_FBFM40_PATH = "/Volumes/SSD1/Projects/ororatech-task/custom_extent_tiles/tile_00_01_FBFM40_V3.tiff"
    
    # Initialize reconciliation processor
    processor = FuelModelReconciliation()
    
    # Optional: Set clouds as NoData instead of default forest
    # processor.clouds_as_nodata = True
    
    # Check input file exists
    if not os.path.exists(INPUT_ESRI_PATH):
        logger.error(f"Input file not found: {INPUT_ESRI_PATH}")
        return
    
    # Run complete reconciliation workflow
    try:
        processor.process_reconciliation(
            input_esri_path=INPUT_ESRI_PATH,
            output_fbfm40_path=OUTPUT_FBFM40_PATH,
            fill_nodata=True,  # Set to False if you want to keep NoData pixels
            keep_original_projection=True  # Keep the same CRS as input (EPSG:3857)
        )
        
        print(f"\n✅ Success! FBFM40 fuel model created: {OUTPUT_FBFM40_PATH}")
        
    except Exception as e:
        logger.error(f"❌ Process failed: {e}")
        return 1


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Enhanced ESRI PFA to FBFM40 Class Reconciliation Script

This script converts ESRI PFA (Potential Fire Activity) land cover classes 
to LANDFIRE FBFM40 (Scott and Burgan Fire Behavior Fuel Models) for fire 
behavior modeling and risk assessment.

Features:
- 1:1 class mapping with validation
- Configuration export/import
- Comprehensive validation
- Reusable mapping framework

Dataset 1 (Target): LANDFIRE FBFM40 (30m, EPSG:5070, values 0-203)
Dataset 2 (Source): ESRI PFA classes (10m, EPSG:3857, values 1-11)

Author: Fire Behavior Modeling Team
Date: 2025
Version: 2.0
"""

import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.enums import Resampling as ResamplingEnum
import numpy as np
import os
import json
from pathlib import Path
import logging
import warnings
from datetime import datetime

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
    """Enhanced class for reconciling ESRI PFA classes to FBFM40 fuel models"""
    
    def __init__(self, mapping_config=None):
        """
        Initialize with default or custom mapping configuration
        
        Args:
            mapping_config (str): Path to JSON configuration file (optional)
        """
        if mapping_config and os.path.exists(mapping_config):
            self.load_mapping_config(mapping_config)
        else:
            self.load_default_mapping()
        
        # Validation flags
        self.validation_passed = False
        self.validation_results = {}
        
    def load_default_mapping(self):
        """Load the default 1:1 class mapping"""
        # Class reconciliation mapping table with confidence scores
        # ESRI PFA Value -> {target, confidence, rationale}
        self.mapping_with_metadata = {
            1: {
                'target': 98, 
                'confidence': 0.95, 
                'rationale': 'Perfect semantic match: Water -> Open Water'
            },
            2: {
                'target': 183, 
                'confidence': 0.55, 
                'rationale': 'Conservative choice: Trees -> Moderate conifer litter (high uncertainty)'
            },
            4: {
                'target': 121, 
                'confidence': 0.60, 
                'rationale': 'Reasonable match: Flooded vegetation -> Grass-shrub mix'
            },
            5: {
                'target': 102, 
                'confidence': 0.75, 
                'rationale': 'Good match: Crops behave like low load grass fuels'
            },
            7: {
                'target': 91, 
                'confidence': 0.90, 
                'rationale': 'Direct match: Built Area -> Urban/Developed'
            },
            8: {
                'target': 99, 
                'confidence': 0.85, 
                'rationale': 'Good match: Bare ground -> Barren'
            },
            9: {
                'target': 92, 
                'confidence': 0.95, 
                'rationale': 'Perfect match: Snow/Ice -> Snow/Ice'
            },
            10: {
                'target': 183, 
                'confidence': 0.20, 
                'rationale': 'Very uncertain: Clouds -> Default forest assumption'
            },
            11: {
                'target': 102, 
                'confidence': 0.70, 
                'rationale': 'Good match: Rangeland -> Low load grass'
            }
        }
        
        # Extract simple mapping for backward compatibility
        self.class_mapping = {k: v['target'] for k, v in self.mapping_with_metadata.items()}
        
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
        
        # Expected source classes for validation
        self.expected_source_classes = [1, 2, 4, 5, 7, 8, 9, 10, 11]
        
        # Valid FBFM40 target classes
        self.valid_fbfm40_classes = [91, 92, 98, 99, 102, 121, 183, 186, 161, 162, 163, 164, 165, 
                                   181, 182, 184, 185, 187, 188, 189, 201, 202, 203, 204]
    
    def load_mapping_config(self, config_path):
        """
        Load mapping configuration from JSON file
        
        Args:
            config_path (str): Path to JSON configuration file
        """
        logger.info(f"Loading mapping configuration from: {config_path}")
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Load mapping data
        if 'mappings' in config:
            self.mapping_with_metadata = {}
            self.class_mapping = {}
            
            for mapping in config['mappings']:
                source_class = mapping['source_class']
                self.mapping_with_metadata[source_class] = {
                    'target': mapping['target_class'],
                    'confidence': mapping.get('confidence', 0.5),
                    'rationale': mapping.get('rationale', 'No rationale provided')
                }
                self.class_mapping[source_class] = mapping['target_class']
        
        # Load other configuration
        self.fbfm40_descriptions = config.get('fbfm40_descriptions', self.fbfm40_descriptions)
        self.expected_source_classes = config.get('expected_source_classes', self.expected_source_classes)
        self.valid_fbfm40_classes = config.get('valid_fbfm40_classes', self.valid_fbfm40_classes)
        
        logger.info(f"Loaded {len(self.class_mapping)} class mappings")
    
    def save_mapping_config(self, output_path):
        """
        Save current mapping configuration to JSON file
        
        Args:
            output_path (str): Path for output JSON file
        """
        config = {
            "metadata": {
                "name": "ESRI_PFA_to_FBFM40_Mapping",
                "version": "2.0",
                "description": "Enhanced 1:1 mapping with confidence scores and validation",
                "creation_date": datetime.now().isoformat(),
                "author": "Fire_Behavior_Team",
                "source_dataset": "ESRI_PFA_Classes",
                "target_dataset": "LANDFIRE_FBFM40",
                "mapping_approach": "Conservative 1:1 mapping prioritizing fire safety"
            },
            "validation_info": {
                "validation_date": datetime.now().isoformat(),
                "validation_passed": self.validation_passed,
                "validation_results": self.validation_results
            },
            "mappings": [],
            "fbfm40_descriptions": self.fbfm40_descriptions,
            "expected_source_classes": self.expected_source_classes,
            "valid_fbfm40_classes": self.valid_fbfm40_classes
        }
        
        # Convert mapping to configuration format
        for source_class, metadata in self.mapping_with_metadata.items():
            config["mappings"].append({
                "source_class": source_class,
                "target_class": metadata['target'],
                "confidence": metadata['confidence'],
                "rationale": metadata['rationale']
            })
        
        with open(output_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Mapping configuration saved: {output_path}")
        return config
    
    def validate_mapping_completeness(self):
        """Validate that all expected source classes are mapped"""
        missing_classes = set(self.expected_source_classes) - set(self.class_mapping.keys())
        
        if missing_classes:
            logger.error(f"Missing mappings for classes: {missing_classes}")
            return False, f"Missing mappings for classes: {missing_classes}"
        
        logger.info("✓ Mapping completeness validation passed")
        return True, "All expected source classes are mapped"
    
    def validate_target_classes(self):
        """Validate that all target FBFM40 classes are valid"""
        invalid_targets = set(self.class_mapping.values()) - set(self.valid_fbfm40_classes)
        
        if invalid_targets:
            logger.error(f"Invalid FBFM40 target classes: {invalid_targets}")
            return False, f"Invalid FBFM40 target classes: {invalid_targets}"
        
        logger.info("✓ Target class validation passed")
        return True, "All target classes are valid FBFM40 codes"
    
    def validate_semantic_logic(self):
        """Validate semantic logic of mappings"""
        validation_rules = {
            1: [98],  # Water should only map to water (NB8)
            7: [91],  # Built areas should only map to urban (NB1)
            9: [92],  # Snow/ice should only map to snow/ice (NB2)
        }
        
        warnings = []
        for source, valid_targets in validation_rules.items():
            if source in self.class_mapping:
                if self.class_mapping[source] not in valid_targets:
                    warning = f"Questionable mapping: {source} -> {self.class_mapping[source]}"
                    warnings.append(warning)
                    logger.warning(warning)
        
        if warnings:
            return False, f"Semantic validation warnings: {warnings}"
        
        logger.info("✓ Semantic logic validation passed")
        return True, "All mappings follow semantic logic"
    
    def validate_confidence_distribution(self):
        """Analyze confidence score distribution"""
        confidences = [meta['confidence'] for meta in self.mapping_with_metadata.values()]
        
        high_conf = sum(1 for c in confidences if c >= 0.8)
        medium_conf = sum(1 for c in confidences if 0.6 <= c < 0.8)
        low_conf = sum(1 for c in confidences if c < 0.6)
        
        avg_confidence = np.mean(confidences)
        
        analysis = {
            'high_confidence_count': high_conf,
            'medium_confidence_count': medium_conf, 
            'low_confidence_count': low_conf,
            'average_confidence': avg_confidence,
            'total_mappings': len(confidences)
        }
        
        logger.info(f"✓ Confidence analysis: Avg={avg_confidence:.2f}, High={high_conf}, Med={medium_conf}, Low={low_conf}")
        return True, analysis
    
    def run_validation_suite(self):
        """Run complete validation suite"""
        logger.info("Running mapping validation suite...")
        
        self.validation_results = {}
        all_passed = True
        
        # Test 1: Completeness
        passed, result = self.validate_mapping_completeness()
        self.validation_results['completeness'] = {'passed': passed, 'result': result}
        all_passed &= passed
        
        # Test 2: Target validity
        passed, result = self.validate_target_classes()
        self.validation_results['target_validity'] = {'passed': passed, 'result': result}
        all_passed &= passed
        
        # Test 3: Semantic logic
        passed, result = self.validate_semantic_logic()
        self.validation_results['semantic_logic'] = {'passed': passed, 'result': result}
        all_passed &= passed
        
        # Test 4: Confidence analysis
        passed, result = self.validate_confidence_distribution()
        self.validation_results['confidence_analysis'] = {'passed': passed, 'result': result}
        
        self.validation_passed = all_passed
        
        if all_passed:
            logger.info("✓ All validation tests passed!")
        else:
            logger.warning("⚠ Some validation tests failed - check results")
        
        return all_passed, self.validation_results
    
    def generate_mapping_documentation(self, output_path=None):
        """Generate human-readable mapping documentation"""
        doc = "# ESRI PFA to FBFM40 Class Mapping Documentation\n\n"
        doc += f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        doc += f"**Version:** 2.0 (Enhanced with validation)\n\n"
        doc += "## Mapping Table\n\n"
        doc += "| Source Class | Source Name | Target Class | Target Name | Confidence | Rationale |\n"
        doc += "|--------------|-------------|--------------|-------------|------------|----------|\n"
        
        source_names = {
            1: "Water", 2: "Trees", 4: "Flooded vegetation", 5: "Crops",
            7: "Built Area", 8: "Bare ground", 9: "Snow/Ice", 10: "Clouds", 11: "Rangeland"
        }
        
        for source, metadata in self.mapping_with_metadata.items():
            target = metadata['target']
            confidence = metadata['confidence']
            rationale = metadata['rationale']
            
            source_name = source_names.get(source, f"Class_{source}")
            target_name = self.fbfm40_descriptions.get(target, f"FBFM_{target}")
            
            doc += f"| {source} | {source_name} | {target} | {target_name} | {confidence:.2f} | {rationale} |\n"
        
        doc += "\n## Validation Summary\n\n"
        if hasattr(self, 'validation_results') and self.validation_results:
            for test_name, test_result in self.validation_results.items():
                status = "✅ PASS" if test_result['passed'] else "❌ FAIL"
                doc += f"- **{test_name.replace('_', ' ').title()}**: {status}\n"
        
        doc += "\n## Usage Instructions\n\n"
        doc += "1. Load this mapping configuration using `load_mapping_config()`\n"
        doc += "2. Run validation using `run_validation_suite()`\n"
        doc += "3. Apply mapping using `process_reconciliation()`\n"
        doc += "4. Review output statistics and confidence scores\n"
        
        if output_path:
            with open(output_path, 'w') as f:
                f.write(doc)
            logger.info(f"Documentation saved: {output_path}")
        
        return doc
    
    def check_input_crs(self, input_path):
        """Check and report the input file CRS"""
        with rasterio.open(input_path) as src:
            logger.info(f"Input file CRS: {src.crs}")
            logger.info(f"Input file shape: {src.shape}")
            logger.info(f"Input file bounds: {src.bounds}")
            logger.info(f"Input file transform: {src.transform}")
            return src.crs
        
    def reproject_and_resample(self, input_path, output_path, target_crs='EPSG:5070', 
                              target_resolution=30, resampling_method=ResamplingEnum.mode):
        """Reproject from EPSG:3857 to EPSG:5070 and resample from 10m to 30m"""
        logger.info(f"Reprojecting and resampling {input_path}")
        
        try:
            with rasterio.open(input_path) as src:
                # Handle PROJ issues by using Well-Known Text if EPSG fails
                try:
                    transform, width, height = calculate_default_transform(
                        src.crs, target_crs, src.width, src.height, *src.bounds,
                        resolution=target_resolution
                    )
                except Exception as e:
                    logger.warning(f"EPSG method failed: {e}")
                    logger.info("Trying alternative CRS definition...")
                    
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
                
                kwargs = src.meta.copy()
                kwargs.update({
                    'crs': target_crs,
                    'transform': transform,
                    'width': width,
                    'height': height,
                    'dtype': 'int16',
                    'nodata': -9999
                })
                
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
        
    def apply_class_mapping_with_confidence(self, input_path, fuel_output_path, confidence_output_path=None):
        """Apply class mapping and optionally generate confidence raster"""
        logger.info(f"Applying class mapping to {input_path}")
        
        with rasterio.open(input_path) as src:
            data = src.read(1)
            
            logger.info(f"Input CRS: {src.crs}")
            logger.info(f"Input shape: {data.shape}")
            
            # Create output arrays
            fuel_output = np.full(data.shape, -9999, dtype=np.int16)
            confidence_output = np.full(data.shape, 0.0, dtype=np.float32)
            
            # Apply mapping with confidence tracking
            for esri_class, metadata in self.mapping_with_metadata.items():
                mask = (data == esri_class)
                if np.any(mask):
                    if esri_class == 10 and self.clouds_as_nodata:
                        fuel_output[mask] = -9999
                        confidence_output[mask] = 0.0
                    else:
                        fuel_output[mask] = metadata['target']
                        confidence_output[mask] = metadata['confidence']
                    
                    pixel_count = np.sum(mask)
                    logger.info(f"Class {esri_class}: {pixel_count:,} pixels -> "
                              f"FBFM {metadata['target']} (confidence: {metadata['confidence']:.2f})")
            
            # Handle unmapped values
            unmapped_mask = ~np.isin(data, list(self.class_mapping.keys()))
            if np.any(unmapped_mask):
                logger.warning(f"Found {np.sum(unmapped_mask)} unmapped pixels, setting to NoData")
                fuel_output[unmapped_mask] = -9999
                confidence_output[unmapped_mask] = 0.0
            
            # Preserve original profile
            profile = src.profile.copy()
            profile.update({
                'dtype': 'int16',
                'nodata': -9999,
                'crs': src.crs,
                'transform': src.transform,
                'width': src.width,
                'height': src.height
            })
            
            # Write fuel model output
            with rasterio.open(fuel_output_path, 'w', **profile) as dst:
                dst.write(fuel_output, 1)
            
            # Write confidence output if requested
            if confidence_output_path:
                profile.update({'dtype': 'float32', 'nodata': 0.0})
                with rasterio.open(confidence_output_path, 'w', **profile) as dst:
                    dst.write(confidence_output, 1)
                logger.info(f"Confidence raster saved: {confidence_output_path}")
                
        logger.info(f"Class mapping complete: {fuel_output_path}")
        
        # Verify CRS preservation
        with rasterio.open(fuel_output_path) as verify:
            logger.info(f"Verified output CRS: {verify.crs}")
            if str(verify.crs) != str(src.crs):
                logger.error(f"CRS mismatch! Expected {src.crs}, got {verify.crs}")

    def apply_class_mapping(self, input_path, output_path):
        """Legacy method for backward compatibility"""
        self.apply_class_mapping_with_confidence(input_path, output_path)
        
    def fill_nodata_majority(self, input_path, output_path, window_size=3):
        """Fill NoData pixels using majority filter from surrounding pixels"""
        from scipy import ndimage
        
        logger.info(f"Filling NoData pixels using {window_size}x{window_size} majority filter")
        
        with rasterio.open(input_path) as src:
            data = src.read(1)
            nodata_mask = (data == -9999)
            
            if not np.any(nodata_mask):
                logger.info("No NoData pixels found, copying input to output")
                import shutil
                shutil.copy2(input_path, output_path)
                return
            
            filled_data = data.copy()
            
            def majority_filter(arr):
                valid_values = arr[arr != -9999]
                if len(valid_values) > 0:
                    unique, counts = np.unique(valid_values, return_counts=True)
                    return unique[np.argmax(counts)]
                return -9999
            
            filled_data = ndimage.generic_filter(
                data, majority_filter, size=window_size, mode='constant', cval=-9999
            )
            
            filled_data[~nodata_mask] = data[~nodata_mask]
            
            profile = src.profile.copy()
            with rasterio.open(output_path, 'w', **profile) as dst:
                dst.write(filled_data, 1)
                
        logger.info(f"NoData filling complete: {output_path}")
        
    def fix_crs(self, raster_path, target_crs):
        """Fix CRS of a raster file by re-writing with correct CRS"""
        logger.info(f"Fixing CRS to {target_crs}")
        
        with rasterio.open(raster_path) as src:
            data = src.read()
            profile = src.profile.copy()
        
        profile['crs'] = target_crs
        
        temp_path = raster_path + '.tmp'
        with rasterio.open(temp_path, 'w', **profile) as dst:
            dst.write(data)
        
        import shutil
        shutil.move(temp_path, raster_path)
        
        logger.info(f"CRS fixed successfully")
        
    def generate_enhanced_statistics_report(self, fuel_output_path, confidence_output_path=None):
        """Generate enhanced statistics report with confidence analysis"""
        logger.info("Generating enhanced statistics report")
        
        with rasterio.open(fuel_output_path) as src:
            fuel_data = src.read(1)
            
            # Load confidence data if available
            confidence_data = None
            if confidence_output_path and os.path.exists(confidence_output_path):
                with rasterio.open(confidence_output_path) as conf_src:
                    confidence_data = conf_src.read(1)
            
            # Calculate statistics
            unique_values, counts = np.unique(fuel_data[fuel_data != -9999], return_counts=True)
            total_pixels = np.sum(counts)
            
            print("\n" + "="*70)
            print("ENHANCED FUEL MODEL RECONCILIATION SUMMARY REPORT")
            print("="*70)
            print(f"Output file: {fuel_output_path}")
            print(f"Total valid pixels: {total_pixels:,}")
            print(f"NoData pixels: {np.sum(fuel_data == -9999):,}")
            
            # Validation status
            if hasattr(self, 'validation_passed'):
                status = "✅ PASSED" if self.validation_passed else "❌ FAILED"
                print(f"Validation status: {status}")
            
            print("\nFuel Model Distribution:")
            print("-" * 70)
            
            for value, count in zip(unique_values, counts):
                percentage = (count / total_pixels) * 100
                description = self.fbfm40_descriptions.get(value, f"Unknown class {value}")
                
                # Add confidence info if available
                conf_info = ""
                if confidence_data is not None:
                    mask = (fuel_data == value)
                    avg_conf = np.mean(confidence_data[mask])
                    conf_info = f" | Conf: {avg_conf:.2f}"
                
                print(f"{value:>3} | {count:>10,} | {percentage:>6.2f}% | {description}{conf_info}")
            
            # Confidence analysis
            if confidence_data is not None:
                print(f"\nConfidence Analysis:")
                print("-" * 70)
                valid_conf = confidence_data[confidence_data > 0]
                if len(valid_conf) > 0:
                    high_conf = np.sum(valid_conf >= 0.8)
                    med_conf = np.sum((valid_conf >= 0.6) & (valid_conf < 0.8))
                    low_conf = np.sum(valid_conf < 0.6)
                    
                    print(f"High confidence (≥0.8): {high_conf:,} ({high_conf/len(valid_conf)*100:.1f}%)")
                    print(f"Medium confidence (0.6-0.8): {med_conf:,} ({med_conf/len(valid_conf)*100:.1f}%)")
                    print(f"Low confidence (<0.6): {low_conf:,} ({low_conf/len(valid_conf)*100:.1f}%)")
                    print(f"Average confidence: {np.mean(valid_conf):.3f}")
            
            print("="*70)
    
    def generate_statistics_report(self, output_path):
        """Legacy method for backward compatibility"""
        self.generate_enhanced_statistics_report(output_path)
            
    def process_reconciliation(self, input_esri_path, output_fbfm40_path, 
                             temp_dir=None, fill_nodata=True, keep_original_projection=False,
                             generate_confidence_raster=False, run_validation=True):
        """
        Enhanced reconciliation workflow with validation and confidence options
        
        Args:
            input_esri_path (str): Path to input ESRI PFA raster
            output_fbfm40_path (str): Path to final FBFM40 output
            temp_dir (str): Directory for temporary files
            fill_nodata (bool): Whether to fill NoData pixels
            keep_original_projection (bool): If True, skip reprojection and keep original CRS
            generate_confidence_raster (bool): Whether to create confidence raster
            run_validation (bool): Whether to run validation suite
        """
        # Run validation suite first
        if run_validation:
            logger.info("Running pre-processing validation...")
            validation_passed, validation_results = self.run_validation_suite()
            if not validation_passed:
                logger.warning("Validation failed - proceeding with caution")
        
        # Setup paths
        if temp_dir is None:
            temp_dir = Path(output_fbfm40_path).parent / "temp"
        
        temp_dir = Path(temp_dir)
        temp_dir.mkdir(exist_ok=True)
        
        temp_reprojected = temp_dir / "esri_pfa_reprojected.tif"
        temp_mapped = temp_dir / "fbfm40_mapped.tif"
        
        # Confidence raster path
        confidence_path = None
        if generate_confidence_raster:
            confidence_path = str(Path(output_fbfm40_path).with_suffix('')) + "_confidence.tif"
        
        try:
            # Check input CRS
            original_crs = self.check_input_crs(input_esri_path)
            
            if keep_original_projection:
                logger.info("Keeping original projection - skipping reprojection step")
                # Apply class mapping directly to input
                self.apply_class_mapping_with_confidence(input_esri_path, temp_mapped, confidence_path)
            else:
                # Reproject and resample
                self.reproject_and_resample(input_esri_path, temp_reprojected)
                # Apply class mapping
                self.apply_class_mapping_with_confidence(temp_reprojected, temp_mapped, confidence_path)
            
            # Fill NoData (optional)
            if fill_nodata:
                self.fill_nodata_majority(temp_mapped, output_fbfm40_path)
                if confidence_path and os.path.exists(confidence_path):
                    # Also fill confidence raster
                    conf_temp = temp_dir / "confidence_filled.tif"
                    self.fill_nodata_majority(confidence_path, conf_temp)
                    import shutil
                    shutil.move(conf_temp, confidence_path)
            else:
                import shutil
                shutil.copy2(temp_mapped, output_fbfm40_path)
            
            # Verify CRS preservation
            if keep_original_projection:
                with rasterio.open(output_fbfm40_path) as final_check:
                    if str(final_check.crs) != str(original_crs):
                        logger.error(f"CRS was not preserved! Original: {original_crs}, Final: {final_check.crs}")
                        logger.info("Attempting to fix CRS...")
                        self.fix_crs(output_fbfm40_path, original_crs)
                        if confidence_path and os.path.exists(confidence_path):
                            self.fix_crs(confidence_path, original_crs)
                    else:
                        logger.info(f"✅ CRS successfully preserved: {final_check.crs}")
            
            # Generate enhanced report
            self.generate_enhanced_statistics_report(output_fbfm40_path, confidence_path)
            
            # Save configuration for reuse
            config_path = str(Path(output_fbfm40_path).with_suffix('')) + "_mapping_config.json"
            self.save_mapping_config(config_path)
            
            # Generate documentation
            doc_path = str(Path(output_fbfm40_path).with_suffix('')) + "_mapping_documentation.md"
            self.generate_mapping_documentation(doc_path)
            
            logger.info(f"Reconciliation complete! Output: {output_fbfm40_path}")
            if confidence_path:
                logger.info(f"Confidence raster: {confidence_path}")
            logger.info(f"Configuration: {config_path}")
            logger.info(f"Documentation: {doc_path}")
            
        except Exception as e:
            logger.error(f"Error during reconciliation: {e}")
            raise
        
        finally:
            # Cleanup temporary files
            for temp_file in temp_dir.glob("*.tif"):
                temp_file.unlink()
            if temp_dir.exists() and not any(temp_dir.iterdir()):
                temp_dir.rmdir()


def main():
    """Main execution function with enhanced options"""
    
    # Configuration
    INPUT_ESRI_PATH = "/Volumes/SSD1/Projects/ororatech-task/custom_extent_tiles/tile_00_01.tiff"
    OUTPUT_FBFM40_PATH = "/Volumes/SSD1/Projects/ororatech-task/custom_extent_tiles/tile_00_01_FBFM40_Enhanced.tiff"
    
    # Optional: Load custom mapping configuration
    # MAPPING_CONFIG = "/path/to/custom_mapping_config.json"
    # processor = FuelModelReconciliation(mapping_config=MAPPING_CONFIG)
    
    # Initialize with default mapping
    processor = FuelModelReconciliation()
    
    # Optional: Set clouds as NoData instead of default forest
    # processor.clouds_as_nodata = True
    
    # Check input file exists
    if not os.path.exists(INPUT_ESRI_PATH):
        logger.error(f"Input file not found: {INPUT_ESRI_PATH}")
        return 1
    
    # Run enhanced reconciliation workflow
    try:
        processor.process_reconciliation(
            input_esri_path=INPUT_ESRI_PATH,
            output_fbfm40_path=OUTPUT_FBFM40_PATH,
            fill_nodata=True,  # Fill NoData pixels
            keep_original_projection=True,  # Keep same CRS as input (EPSG:3857)
            generate_confidence_raster=True,  # Create confidence score raster
            run_validation=True  # Run validation suite
        )
        
        print(f"\n✅ Success! Enhanced FBFM40 fuel model created!")
        print(f"📁 Main output: {OUTPUT_FBFM40_PATH}")
        print(f"📊 Confidence raster: {OUTPUT_FBFM40_PATH.replace('.tiff', '_confidence.tif')}")
        print(f"⚙️ Configuration: {OUTPUT_FBFM40_PATH.replace('.tiff', '_mapping_config.json')}")
        print(f"📖 Documentation: {OUTPUT_FBFM40_PATH.replace('.tiff', '_mapping_documentation.md')}")
        print("\nNote: Output retains original coordinate system and resolution from input file")
        
    except Exception as e:
        logger.error(f"❌ Process failed: {e}")
        return 1


if __name__ == "__main__":
    main()
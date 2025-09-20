#!/usr/bin/env python3
"""
Simple Confidence Mapping Without Auxiliary Data
Based on expert knowledge and inherent class uncertainty
"""

import rasterio
import numpy as np
import json

class SimpleConfidenceMapper:
    def __init__(self):
        # Enhanced mapping with confidence scores
        self.mapping_with_confidence = {
            1: {'target': 98, 'confidence': 0.95, 'rationale': 'Perfect match: Water -> Water'},
            2: {'target': 183, 'confidence': 0.55, 'rationale': 'Uncertain: Trees could be various forest types'},
            4: {'target': 121, 'confidence': 0.60, 'rationale': 'Moderate: Flooded vegetation -> Mixed grass-shrub'},
            5: {'target': 102, 'confidence': 0.75, 'rationale': 'Good: Crops behave like grass fuels'},
            7: {'target': 91, 'confidence': 0.90, 'rationale': 'Excellent: Built area -> Urban'},
            8: {'target': 99, 'confidence': 0.85, 'rationale': 'Good: Bare ground -> Barren'},
            9: {'target': 92, 'confidence': 0.95, 'rationale': 'Perfect match: Snow/Ice -> Snow/Ice'},
            10: {'target': 183, 'confidence': 0.20, 'rationale': 'Very uncertain: Clouds -> Default assumption'},
            11: {'target': 102, 'confidence': 0.70, 'rationale': 'Good: Rangeland -> Grass fuels'}
        }
    
    def apply_mapping_with_confidence(self, input_path, fuel_output_path, confidence_output_path):
        """Apply mapping and generate confidence raster"""
        
        with rasterio.open(input_path) as src:
            input_data = src.read(1)
            profile = src.profile.copy()
            
            # Create output arrays
            fuel_output = np.full(input_data.shape, -9999, dtype=np.int16)
            confidence_output = np.full(input_data.shape, 0.0, dtype=np.float32)
            
            # Apply mapping
            for source_class, mapping_info in self.mapping_with_confidence.items():
                mask = (input_data == source_class)
                if np.any(mask):
                    fuel_output[mask] = mapping_info['target']
                    confidence_output[mask] = mapping_info['confidence']
                    
                    pixel_count = np.sum(mask)
                    print(f"Class {source_class}: {pixel_count:,} pixels -> "
                          f"FBFM {mapping_info['target']} "
                          f"(confidence: {mapping_info['confidence']:.2f})")
            
            # Handle unmapped values
            unmapped_mask = ~np.isin(input_data, list(self.mapping_with_confidence.keys()))
            if np.any(unmapped_mask):
                print(f"Warning: {np.sum(unmapped_mask):,} unmapped pixels set to NoData")
            
            # Save fuel model output
            profile.update({'dtype': 'int16', 'nodata': -9999})
            with rasterio.open(fuel_output_path, 'w', **profile) as dst:
                dst.write(fuel_output, 1)
            
            # Save confidence output  
            profile.update({'dtype': 'float32', 'nodata': 0.0})
            with rasterio.open(confidence_output_path, 'w', **profile) as dst:
                dst.write(confidence_output, 1)
                
            print(f"\nOutputs created:")
            print(f"- Fuel models: {fuel_output_path}")
            print(f"- Confidence scores: {confidence_output_path}")
    
    def analyze_confidence_distribution(self, confidence_path):
        """Analyze the distribution of confidence scores"""
        
        with rasterio.open(confidence_path) as src:
            confidence_data = src.read(1)
            
            valid_confidence = confidence_data[confidence_data > 0]
            
            print(f"\n{'='*50}")
            print("CONFIDENCE SCORE ANALYSIS")
            print(f"{'='*50}")
            print(f"Total mapped pixels: {len(valid_confidence):,}")
            
            # Confidence categories
            high_conf = np.sum(valid_confidence >= 0.8)
            med_conf = np.sum((valid_confidence >= 0.6) & (valid_confidence < 0.8))
            low_conf = np.sum(valid_confidence < 0.6)
            
            total = len(valid_confidence)
            print(f"High confidence (≥0.8): {high_conf:,} ({high_conf/total*100:.1f}%)")
            print(f"Medium confidence (0.6-0.8): {med_conf:,} ({med_conf/total*100:.1f}%)")
            print(f"Low confidence (<0.6): {low_conf:,} ({low_conf/total*100:.1f}%)")
            print(f"Average confidence: {np.mean(valid_confidence):.3f}")
            
            # Class-specific confidence
            print(f"\nConfidence by original class:")
            for source_class, mapping_info in self.mapping_with_confidence.items():
                conf = mapping_info['confidence']
                print(f"  Class {source_class}: {conf:.2f} - {mapping_info['rationale']}")
            
            print(f"{'='*50}")
    
    def create_confidence_config(self, output_path="confidence_mapping_config.json"):
        """Save mapping configuration for reuse"""
        
        config = {
            "metadata": {
                "name": "ESRI_PFA_to_FBFM40_Simple_Confidence",
                "version": "1.0", 
                "description": "Simple confidence mapping without auxiliary data",
                "confidence_basis": "Expert knowledge and semantic similarity"
            },
            "confidence_categories": {
                "high": {"range": [0.8, 1.0], "description": "Direct semantic matches"},
                "medium": {"range": [0.6, 0.8], "description": "Reasonable generalizations"},
                "low": {"range": [0.0, 0.6], "description": "Uncertain mappings"}
            },
            "mappings": []
        }
        
        # Convert to config format
        for source_class, mapping_info in self.mapping_with_confidence.items():
            config["mappings"].append({
                "source_class": source_class,
                "target_class": mapping_info['target'],
                "confidence": mapping_info['confidence'],
                "rationale": mapping_info['rationale']
            })
        
        with open(output_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"Configuration saved: {output_path}")
        return config

def main():
    """Example usage"""
    
    # File paths
    input_path = "/Volumes/SSD1/Projects/ororatech-task/custom_extent_tiles/tile_01_01.tiff"
    fuel_output = "/Volumes/SSD1/Projects/ororatech-task/custom_extent_tiles/tile_01_01_FBFM40_confidence.tiff"
    confidence_output = "/Volumes/SSD1/Projects/ororatech-task/custom_extent_tiles/tile_01_01_confidence_scores.tiff"
    
    # Initialize mapper
    mapper = SimpleConfidenceMapper()
    
    # Create configuration file
    config = mapper.create_confidence_config()
    
    # Apply mapping with confidence (uncomment to run)
    # mapper.apply_mapping_with_confidence(input_path, fuel_output, confidence_output)
    
    # Analyze results (uncomment to run)
    # mapper.analyze_confidence_distribution(confidence_output)
    
    print("\nBenefits of this approach:")
    print("✓ No auxiliary data required")
    print("✓ Quantifies mapping uncertainty") 
    print("✓ Identifies areas needing validation")
    print("✓ Reusable configuration")
    print("✓ Quality assessment metrics")

if __name__ == "__main__":
    main()
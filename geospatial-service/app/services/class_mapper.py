from typing import Dict, List, Any, Optional
import json
from pathlib import Path
from app.models.dataset import ClassMapping, ClassificationSystem

class ClassReconciler:
    def __init__(self):
        self.known_mappings = self._load_mapping_database()

    def _load_mapping_database(self) -> Dict[str, Any]:
        """Load pre-defined class mapping database with comprehensive fuel model mappings"""
        return {
            "FBFM40": {
                "is_canonical": True,
                "description": "Anderson Fire Behavior Fuel Models (40 classes)",
                "classes": {
                    1: {"name": "Short Grass (1 ft)", "group": "grass", "load": "low"},
                    2: {"name": "Timber (Grass and Understory)", "group": "grass", "load": "low"},
                    3: {"name": "Tall Grass (2.5 ft)", "group": "grass", "load": "low"},
                    4: {"name": "Chaparral (6 ft)", "group": "chaparral", "load": "moderate"},
                    5: {"name": "Brush (2 ft)", "group": "shrub", "load": "low"},
                    6: {"name": "Dormant Brush, Hardwood Slash", "group": "shrub", "load": "moderate"},
                    7: {"name": "Southern Rough", "group": "shrub", "load": "moderate"},
                    8: {"name": "Closed Timber Litter", "group": "timber", "load": "low"},
                    9: {"name": "Hardwood Litter", "group": "timber", "load": "moderate"},
                    10: {"name": "Timber (Litter and Understory)", "group": "timber", "load": "moderate"},
                    11: {"name": "Light Logging Slash", "group": "slash", "load": "low"},
                    12: {"name": "Medium Logging Slash", "group": "slash", "load": "moderate"},
                    13: {"name": "Heavy Logging Slash", "group": "slash", "load": "high"},
                    14: {"name": "Low Load, Dry Climate Shrub", "group": "shrub", "load": "low"},
                    15: {"name": "High Load, Dry Climate Shrub", "group": "shrub", "load": "high"},
                    91: {"name": "Urban or Developed", "group": "non-burnable", "load": "none"},
                    92: {"name": "Snow or Ice", "group": "non-burnable", "load": "none"},
                    93: {"name": "Agriculture", "group": "non-burnable", "load": "none"},
                    98: {"name": "Water", "group": "non-burnable", "load": "none"},
                    99: {"name": "Barren or Sparsely Vegetated", "group": "non-burnable", "load": "none"}
                }
            },

            "SENTINEL_FUEL_2024": {
                "description": "Sentinel-derived fuel classification 2024",
                "source": "Satellite-derived",
                "mappings_to_fbfm40": {
                    1: {"target": 1, "confidence": 0.95, "method": "spectral_similarity"},
                    2: {"target": 2, "confidence": 0.87, "method": "vegetation_structure"},
                    3: {"target": 3, "confidence": 0.91, "method": "height_analysis"},
                    4: {"target": 4, "confidence": 0.82, "method": "density_classification"},
                    5: {"target": 5, "confidence": 0.89, "method": "canopy_cover"},
                    10: {"target": 14, "confidence": 0.91, "method": "climate_adjusted"},
                    11: {"target": 15, "confidence": 0.88, "method": "load_estimation"},
                    20: {"target": 8, "confidence": 0.89, "method": "forest_type"},
                    21: {"target": 9, "confidence": 0.85, "method": "deciduous_classification"},
                    22: {"target": 10, "confidence": 0.87, "method": "mixed_forest"},
                    30: {"target": 11, "confidence": 0.75, "method": "disturbance_detection"},
                    31: {"target": 12, "confidence": 0.78, "method": "slash_estimation"},
                    100: {"target": 91, "confidence": 0.98, "method": "land_use_classification"},
                    101: {"target": 93, "confidence": 0.96, "method": "agricultural_masking"},
                    102: {"target": 98, "confidence": 0.99, "method": "water_detection"},
                    103: {"target": 99, "confidence": 0.94, "method": "bare_soil_classification"}
                }
            },

            "LANDFIRE_US": {
                "description": "LANDFIRE Fuel Model data (US)",
                "source": "USGS/USFS",
                "mappings_to_fbfm40": {
                    101: {"target": 1, "confidence": 0.93, "method": "direct_correspondence"},
                    102: {"target": 2, "confidence": 0.88, "method": "vegetation_type"},
                    103: {"target": 3, "confidence": 0.91, "method": "grass_height"},
                    104: {"target": 4, "confidence": 0.89, "method": "shrub_density"},
                    105: {"target": 5, "confidence": 0.87, "method": "brush_classification"},
                    106: {"target": 6, "confidence": 0.85, "method": "dormant_vegetation"},
                    107: {"target": 7, "confidence": 0.83, "method": "southern_vegetation"},
                    108: {"target": 8, "confidence": 0.92, "method": "forest_floor"},
                    109: {"target": 9, "confidence": 0.89, "method": "hardwood_litter"},
                    110: {"target": 10, "confidence": 0.91, "method": "understory_analysis"},
                    201: {"target": 14, "confidence": 0.85, "method": "climate_classification"},
                    202: {"target": 15, "confidence": 0.87, "method": "shrub_load_analysis"},
                    301: {"target": 11, "confidence": 0.78, "method": "logging_history"},
                    302: {"target": 12, "confidence": 0.81, "method": "slash_density"},
                    303: {"target": 13, "confidence": 0.84, "method": "heavy_disturbance"},
                    901: {"target": 91, "confidence": 0.97, "method": "urban_classification"},
                    902: {"target": 92, "confidence": 0.99, "method": "snow_ice_detection"},
                    903: {"target": 93, "confidence": 0.95, "method": "agricultural_land"},
                    998: {"target": 98, "confidence": 0.99, "method": "water_body_detection"},
                    999: {"target": 99, "confidence": 0.92, "method": "barren_land"}
                }
            },

            "CANADIAN_FBP": {
                "description": "Canadian Forest Fire Behavior Prediction System",
                "source": "Canadian Forest Service",
                "mappings_to_fbfm40": {
                    # Conifer types
                    "C1": {"target": 8, "confidence": 0.89, "method": "conifer_correspondence"},
                    "C2": {"target": 9, "confidence": 0.87, "method": "boreal_forest"},
                    "C3": {"target": 10, "confidence": 0.85, "method": "mature_conifer"},
                    "C4": {"target": 10, "confidence": 0.83, "method": "immature_conifer"},
                    "C5": {"target": 11, "confidence": 0.81, "method": "red_green_pine"},
                    "C6": {"target": 12, "confidence": 0.79, "method": "conifer_plantation"},
                    "C7": {"target": 13, "confidence": 0.77, "method": "ponderosa_pine"},
                    # Deciduous types
                    "D1": {"target": 9, "confidence": 0.91, "method": "leafless_aspen"},
                    "D2": {"target": 9, "confidence": 0.89, "method": "green_aspen"},
                    # Mixedwood
                    "M1": {"target": 10, "confidence": 0.85, "method": "boreal_mixedwood"},
                    "M2": {"target": 10, "confidence": 0.83, "method": "boreal_mixedwood"},
                    # Slash
                    "S1": {"target": 11, "confidence": 0.87, "method": "jack_lodgepole_slash"},
                    "S2": {"target": 12, "confidence": 0.85, "method": "white_spruce_slash"},
                    "S3": {"target": 13, "confidence": 0.83, "method": "coastal_cedar_slash"},
                    # Open/Non-fuel
                    "O1a": {"target": 1, "confidence": 0.92, "method": "matted_grass"},
                    "O1b": {"target": 2, "confidence": 0.90, "method": "standing_grass"},
                    "NF": {"target": 99, "confidence": 0.95, "method": "non_fuel"}
                }
            }
        }

    async def detect_classification_system(self, detected_classes: List[int]) -> str:
        """Detect which classification system is being used based on class values"""

        if not detected_classes:
            return ClassificationSystem.UNKNOWN

        # Convert to set for faster lookups
        class_set = set(detected_classes)

        # Check if already FBFM40 (canonical system)
        fbfm40_classes = set(range(1, 41)) | {91, 92, 93, 98, 99}
        if class_set.issubset(fbfm40_classes) and any(c in class_set for c in range(1, 16)):
            return ClassificationSystem.FBFM40

        # Check for LANDFIRE-like patterns (100+ values)
        if any(cls > 100 and cls < 1000 for cls in detected_classes):
            landfire_patterns = {101, 102, 103, 108, 109, 110, 201, 202, 301, 902, 998}
            if any(cls in landfire_patterns for cls in detected_classes):
                return ClassificationSystem.LANDFIRE_US

        # Check for Sentinel-like patterns
        sentinel_patterns = {1, 2, 3, 4, 5, 10, 11, 20, 21, 22, 30, 31, 100, 101, 102, 103}
        if len(class_set.intersection(sentinel_patterns)) >= 3:
            return ClassificationSystem.SENTINEL_FUEL_2024

        # Pattern-based detection
        max_value = max(detected_classes)
        min_value = min(detected_classes)

        # Small range with specific patterns suggests Sentinel
        if max_value <= 150 and min_value >= 1:
            if any(cls in {10, 20, 30, 100} for cls in detected_classes):
                return ClassificationSystem.SENTINEL_FUEL_2024

        # Very high values suggest LANDFIRE
        if max_value > 300:
            return ClassificationSystem.LANDFIRE_US

        return ClassificationSystem.UNKNOWN

    async def create_class_mapping(
        self,
        source_system: str,
        detected_classes: List[int],
        confidence_threshold: float = 0.8
    ) -> ClassMapping:
        """Create comprehensive mapping from source system to FBFM40"""

        # Handle already canonical system
        if source_system == ClassificationSystem.FBFM40:
            return ClassMapping(
                source_system=ClassificationSystem.FBFM40,
                target_system="FBFM40",
                mapping_required=False,
                direct_mapping=True,
                auto_mappable=True,
                mappings={cls: cls for cls in detected_classes},
                confidence_scores={cls: 1.0 for cls in detected_classes},
                auto_mapped_count=len(detected_classes),
                manual_review_count=0
            )

        # Handle unknown systems
        if source_system not in self.known_mappings:
            return ClassMapping(
                source_system=source_system,
                target_system="FBFM40",
                mapping_required=True,
                auto_mappable=False,
                unmapped_classes=detected_classes,
                auto_mapped_count=0,
                manual_review_count=len(detected_classes)
            )

        # Generate mappings for known systems
        system_mappings = self.known_mappings[source_system]["mappings_to_fbfm40"]

        mappings = {}
        confidence_scores = {}
        unmapped = []
        high_confidence_count = 0

        for cls in detected_classes:
            cls_key = str(cls) if cls not in system_mappings else cls

            if cls_key in system_mappings:
                mapping_info = system_mappings[cls_key]
                target = mapping_info["target"]
                confidence = mapping_info["confidence"]

                mappings[cls] = target
                confidence_scores[cls] = confidence

                if confidence >= confidence_threshold:
                    high_confidence_count += 1
            else:
                unmapped.append(cls)

        # Determine if system is auto-mappable
        mapped_percentage = len(mappings) / len(detected_classes) if detected_classes else 0
        high_confidence_percentage = high_confidence_count / len(detected_classes) if detected_classes else 0

        auto_mappable = (mapped_percentage >= 0.7 and high_confidence_percentage >= 0.5)

        return ClassMapping(
            source_system=source_system,
            target_system="FBFM40",
            mapping_required=True,
            auto_mappable=auto_mappable,
            mappings=mappings,
            confidence_scores=confidence_scores,
            unmapped_classes=unmapped,
            auto_mapped_count=len(mappings),
            manual_review_count=len(unmapped)
        )

    async def get_mapping_recommendations(
        self,
        source_system: str,
        unmapped_classes: List[int]
    ) -> Dict[int, List[Dict[str, Any]]]:
        """Provide mapping recommendations for unmapped classes"""

        recommendations = {}
        fbfm40_classes = self.known_mappings["FBFM40"]["classes"]

        for cls in unmapped_classes:
            suggestions = []

            # Rule-based suggestions based on value ranges
            if cls <= 10:
                # Low values often map to grass/low fuel
                suggestions.extend([
                    {"target": 1, "reason": "Low value suggests grass fuel", "confidence": 0.6},
                    {"target": 2, "reason": "Could be timber-grass mix", "confidence": 0.5},
                    {"target": 5, "reason": "Possible low shrub", "confidence": 0.4}
                ])
            elif cls <= 20:
                # Medium values often map to shrub/timber
                suggestions.extend([
                    {"target": 4, "reason": "Medium value suggests chaparral", "confidence": 0.6},
                    {"target": 6, "reason": "Could be brush/hardwood", "confidence": 0.5},
                    {"target": 8, "reason": "Possible timber litter", "confidence": 0.4}
                ])
            elif cls <= 40:
                # Higher values might be heavy fuels
                suggestions.extend([
                    {"target": 10, "reason": "Higher value suggests heavy timber", "confidence": 0.6},
                    {"target": 12, "reason": "Could be medium slash", "confidence": 0.5},
                    {"target": 13, "reason": "Possible heavy slash", "confidence": 0.4}
                ])
            elif cls >= 90:
                # Very high values often non-burnable
                suggestions.extend([
                    {"target": 91, "reason": "High value suggests urban/developed", "confidence": 0.7},
                    {"target": 98, "reason": "Could be water", "confidence": 0.6},
                    {"target": 99, "reason": "Possible barren land", "confidence": 0.5}
                ])

            recommendations[cls] = suggestions[:3]  # Top 3 suggestions

        return recommendations

    async def validate_mapping(
        self,
        mapping: Dict[int, int]
    ) -> Dict[str, Any]:
        """Validate a proposed class mapping"""

        validation_result = {
            "is_valid": True,
            "warnings": [],
            "errors": [],
            "statistics": {}
        }

        fbfm40_classes = set(self.known_mappings["FBFM40"]["classes"].keys())
        target_values = list(mapping.values())

        # Check for invalid target classes
        invalid_targets = [t for t in target_values if t not in fbfm40_classes]
        if invalid_targets:
            validation_result["errors"].extend([
                f"Invalid FBFM40 class: {t}" for t in invalid_targets
            ])
            validation_result["is_valid"] = False

        # Check for missing critical classes
        critical_classes = {1, 2, 8, 91, 98}  # Common essential classes
        mapped_targets = set(target_values)
        if not any(c in mapped_targets for c in critical_classes):
            validation_result["warnings"].append(
                "No mappings to common fuel classes (grass, timber, urban, water)"
            )

        # Statistics
        validation_result["statistics"] = {
            "total_mappings": len(mapping),
            "unique_targets": len(set(target_values)),
            "most_common_target": max(set(target_values), key=target_values.count) if target_values else None,
            "target_distribution": {t: target_values.count(t) for t in set(target_values)}
        }

        return validation_result
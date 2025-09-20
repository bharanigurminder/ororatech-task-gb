# ESRI PFA to FBFM40 Class Mapping Documentation

**Generated:** 2025-09-21 04:55:16

**Version:** 2.0 (Enhanced with validation)

## Mapping Table

| Source Class | Source Name | Target Class | Target Name | Confidence | Rationale |
|--------------|-------------|--------------|-------------|------------|----------|
| 1 | Water | 98 | NB8 - Open Water | 0.95 | Perfect semantic match: Water -> Open Water |
| 2 | Trees | 183 | TL3 - Moderate load conifer litter | 0.55 | Conservative choice: Trees -> Moderate conifer litter (high uncertainty) |
| 4 | Flooded vegetation | 121 | GS1 - Low load, dry climate grass-shrub | 0.60 | Reasonable match: Flooded vegetation -> Grass-shrub mix |
| 5 | Crops | 102 | GR2 - Low load, dry climate grass | 0.75 | Good match: Crops behave like low load grass fuels |
| 7 | Built Area | 91 | NB1 - Urban/Developed | 0.90 | Direct match: Built Area -> Urban/Developed |
| 8 | Bare ground | 99 | NB9 - Barren | 0.85 | Good match: Bare ground -> Barren |
| 9 | Snow/Ice | 92 | NB2 - Snow/Ice | 0.95 | Perfect match: Snow/Ice -> Snow/Ice |
| 10 | Clouds | 183 | TL3 - Moderate load conifer litter | 0.20 | Very uncertain: Clouds -> Default forest assumption |
| 11 | Rangeland | 102 | GR2 - Low load, dry climate grass | 0.70 | Good match: Rangeland -> Low load grass |

## Validation Summary

- **Completeness**: ✅ PASS
- **Target Validity**: ✅ PASS
- **Semantic Logic**: ✅ PASS
- **Confidence Analysis**: ✅ PASS

## Usage Instructions

1. Load this mapping configuration using `load_mapping_config()`
2. Run validation using `run_validation_suite()`
3. Apply mapping using `process_reconciliation()`
4. Review output statistics and confidence scores

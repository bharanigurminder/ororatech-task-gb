#!/bin/bash
echo "Merging tiles..."
gdal_merge.py -o custom_extent_landcover_10m_merged.tiff -of GTiff -co COMPRESS=LZW -co TILED=YES custom_extent_tiles/*.tiff
echo "Done: custom_extent_landcover_10m_merged.tiff"

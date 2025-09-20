import requests
import os
from math import ceil

def download_custom_extent_10m():
    """
    Download your specific extent at true 10m resolution
    """
    
    # Your extent in Web Mercator
    extent = {
        'xmin': -13409254.2,
        'ymin': 4420128.8,
        'xmax': -13271906.3,
        'ymax': 4535832.2
    }
    
    # Calculate full dimensions at 10m
    width_m = extent['xmax'] - extent['xmin']
    height_m = extent['ymax'] - extent['ymin']
    width_pixels = int(width_m / 10)
    height_pixels = int(height_m / 10)
    
    print(f"Full extent dimensions at 10m resolution:")
    print(f"  {width_pixels} x {height_pixels} pixels")
    print(f"  {width_m/1000:.1f} x {height_m/1000:.1f} km")
    
    # Check if we need to tile
    max_pixels = 8000
    if width_pixels <= max_pixels and height_pixels <= max_pixels:
        # Single download
        print(f"\nCan download as single file (within {max_pixels}x{max_pixels} limit)")
        download_single_file(extent, width_pixels, height_pixels)
    else:
        # Need to tile
        print(f"\nNeed to tile (exceeds {max_pixels}x{max_pixels} limit)")
        download_tiled(extent, width_m, height_m, max_pixels)

def download_single_file(extent, width, height):
    """Download as single file"""
    
    url = "https://ic.imagery1.arcgis.com/arcgis/rest/services/Sentinel2_10m_LandCover/ImageServer/exportImage"
    
    params = {
        'f': 'image',
        'bbox': f"{extent['xmin']},{extent['ymin']},{extent['xmax']},{extent['ymax']}",
        'bboxSR': '102100',
        'imageSR': '102100',
        'size': f"{width},{height}",
        'format': 'tiff',
        'mosaicRule': '{"ascending":true,"mosaicMethod":"esriMosaicAttribute","mosaicOperation":"MT_FIRST","sortField":"Year","sortValue":"2023"}',
        'time': '1672531200000,1704067199000'
    }
    
    print(f"Downloading single file: {width}x{height} pixels")
    
    try:
        response = requests.get(url, params=params, timeout=300)
        response.raise_for_status()
        
        filename = "custom_extent_landcover_10m.tiff"
        with open(filename, 'wb') as f:
            f.write(response.content)
        
        print(f"✓ Downloaded: {filename}")
        print(f"  File size: {len(response.content) / (1024*1024):.1f} MB")
        
    except Exception as e:
        print(f"✗ Error: {e}")

def download_tiled(extent, width_m, height_m, max_pixels):
    """Download in tiles for true 10m resolution"""
    
    # Calculate tile size in meters to stay under pixel limit
    tile_size_m = (max_pixels - 100) * 10  # Leave some margin
    
    x_tiles = ceil(width_m / tile_size_m)
    y_tiles = ceil(height_m / tile_size_m)
    
    print(f"Creating {x_tiles} x {y_tiles} = {x_tiles * y_tiles} tiles")
    print(f"Each tile: ~{tile_size_m/1000:.1f}km x {tile_size_m/1000:.1f}km")
    
    os.makedirs("custom_extent_tiles", exist_ok=True)
    
    url = "https://ic.imagery1.arcgis.com/arcgis/rest/services/Sentinel2_10m_LandCover/ImageServer/exportImage"
    
    for i in range(x_tiles):
        for j in range(y_tiles):
            # Calculate tile bounds
            xmin = extent['xmin'] + (i * tile_size_m)
            xmax = min(xmin + tile_size_m, extent['xmax'])
            ymin = extent['ymin'] + (j * tile_size_m)
            ymax = min(ymin + tile_size_m, extent['ymax'])
            
            # Calculate pixels for this tile
            tile_width = int((xmax - xmin) / 10)
            tile_height = int((ymax - ymin) / 10)
            
            params = {
                'f': 'image',
                'bbox': f"{xmin},{ymin},{xmax},{ymax}",
                'bboxSR': '102100',
                'imageSR': '102100',
                'size': f"{tile_width},{tile_height}",
                'format': 'tiff',
                'mosaicRule': '{"ascending":true,"mosaicMethod":"esriMosaicAttribute","mosaicOperation":"MT_FIRST","sortField":"Year","sortValue":"2023"}',
                'time': '1672531200000,1704067199000'
            }
            
            filename = f"custom_extent_tiles/tile_{i:02d}_{j:02d}.tiff"
            
            try:
                print(f"Downloading tile {i+1}/{x_tiles}, {j+1}/{y_tiles}: {tile_width}x{tile_height} pixels")
                
                response = requests.get(url, params=params, timeout=300)
                response.raise_for_status()
                
                with open(filename, 'wb') as f:
                    f.write(response.content)
                
                print(f"  ✓ {len(response.content) / (1024*1024):.1f} MB")
                
            except Exception as e:
                print(f"  ✗ Error: {e}")
    
    # Create merge script
    merge_script = '''#!/bin/bash
echo "Merging tiles..."
gdal_merge.py -o custom_extent_landcover_10m_merged.tiff -of GTiff -co COMPRESS=LZW -co TILED=YES custom_extent_tiles/*.tiff
echo "Done: custom_extent_landcover_10m_merged.tiff"
'''
    
    with open('merge_custom_tiles.sh', 'w') as f:
        f.write(merge_script)
    os.chmod('merge_custom_tiles.sh', 0o755)
    
    print(f"\nRun './merge_custom_tiles.sh' to combine tiles")

if __name__ == "__main__":
    download_custom_extent_10m()
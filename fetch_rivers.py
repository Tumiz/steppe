#!/usr/bin/env python3
"""Fetch river geometries from Natural Earth and update rivers.json."""

import json
import urllib.request
import zipfile
import os
import shapefile

# Rivers to extract (name patterns to search for in Natural Earth data)
RIVER_SEARCH = {
    "Dnieper River": ["Dnieper", "Dnepr"],
    "Dniester River": ["Dniester", "Dnister"],
    "Southern Bug River": ["Bug"],
    "Don River": ["Don"],
    "Seversky Donets River": ["Donets"],
    "Volga River": ["Volga"],
    "Ural River": ["Ural"],
    "Emba River": ["Emba"],
    "Kuban River": ["Kuban"],
    "Terek River": ["Terek"],
    "Kuma River": ["Kuma"],
    "Tobol River": ["Tobol"],
    "Ishim River": ["Ishim"],
    "Irtysh River": ["Irtysh"],
    "Ob River": ["Ob"],
    "Tom River": ["Tom"],
    "Yenisei River": ["Yenisei"],
    "Angara River": ["Angara"],
    "Selenga River": ["Selenga"],
    "Orkhon River": ["Orkhon"],
    "Tuul River": ["Tuul"],
    "Kerulen River": ["Kerulen", "Хэрлэн"],
    "Syr Darya River": ["Syr Darya", "Sirdaryo"],
    "Amu Darya River": ["Amu Darya", "Amudaryo"],
    "Ili River": ["Ili"],
    "Chu River": ["Chu"],
    "Zeravshan River": ["Zeravshan"],
    "Tarim River": ["Tarim"],
    "Yellow River (Huang He)": ["Yellow", "Huang"],
    "Wei River": ["Wei"],
    "Liao River": ["Liao"],
}

# Fallback coordinates for rivers not in Natural Earth
FALLBACK_RIVERS = {
    "Emba River": [[57.0, 51.5], [56.5, 51.0], [56.0, 50.5], [55.5, 50.0], [55.0, 49.5], [54.5, 49.0], [54.0, 48.5], [53.5, 48.0], [53.0, 47.5], [52.5, 47.0], [52.0, 46.8]],
    "Terek River": [[44.0, 43.0], [44.3, 43.2], [44.5, 43.4], [44.8, 43.6], [45.0, 43.7], [45.5, 43.8], [46.0, 44.0], [46.5, 44.3], [47.0, 44.5], [47.5, 44.0]],
    "Kuma River": [[43.0, 44.0], [43.5, 44.2], [44.0, 44.5], [44.5, 44.8], [45.0, 45.0], [45.5, 45.2], [46.0, 45.5], [46.5, 45.8], [47.0, 45.5]],
    "Yenisei River": [[92.0, 50.0], [92.5, 50.5], [93.0, 51.0], [93.2, 51.5], [93.5, 52.0], [93.3, 52.5], [93.0, 53.0], [92.9, 53.5], [92.9, 54.0], [92.9, 54.5], [92.9, 55.0], [92.9, 55.5], [93.0, 56.0], [93.5, 56.5], [94.0, 57.0], [94.5, 57.5], [95.0, 58.0], [95.5, 58.5], [96.0, 59.0], [96.5, 59.5], [97.0, 60.0], [97.5, 60.5], [98.0, 61.0], [98.5, 61.5], [99.0, 62.0], [99.5, 62.5], [100.0, 63.0], [100.5, 63.5], [101.0, 64.0], [101.5, 64.5], [102.0, 65.0], [102.5, 65.5], [103.0, 66.0], [103.5, 66.5], [104.0, 67.0], [104.5, 67.5], [105.0, 68.0], [105.5, 68.5], [106.0, 69.0], [106.5, 69.5], [107.0, 70.0], [107.5, 70.5], [108.0, 71.0]],
    "Orkhon River": [[101.5, 47.5], [102.0, 47.8], [102.5, 48.0], [103.0, 48.3], [103.5, 48.6], [104.0, 48.9], [104.5, 49.2], [105.0, 49.5], [105.5, 49.8], [106.0, 50.0]],
    "Tuul River": [[107.0, 47.0], [107.0, 47.3], [106.9, 47.6], [106.9, 47.9], [106.9, 48.2], [106.8, 48.5], [106.7, 48.8], [106.5, 49.1], [106.3, 49.4], [106.0, 49.7], [106.0, 50.0]],
    "Kerulen River": [[109.0, 47.0], [109.5, 47.2], [110.0, 47.4], [110.5, 47.6], [111.0, 47.8], [111.5, 47.9], [112.0, 48.0], [112.5, 48.0], [113.0, 48.0], [113.5, 48.0], [114.0, 48.0], [114.5, 48.0], [115.0, 48.0], [115.5, 48.0], [116.0, 48.0]],
    "Zeravshan River": [[68.0, 38.5], [67.5, 38.8], [67.0, 39.0], [66.5, 39.3], [66.0, 39.5], [65.5, 39.7], [65.0, 39.8], [64.5, 39.9], [64.0, 40.0], [63.5, 40.1], [63.0, 40.2], [62.5, 40.3], [62.0, 40.4], [61.5, 40.5]],
}

NATURAL_EARTH_URL = "https://naciscdn.org/naturalearth/10m/physical/ne_10m_rivers_lake_centerlines.zip"
TEMP_DIR = "/tmp/rivers_ne"
SHAPEFILE_PATH = os.path.join(TEMP_DIR, "ne_10m_rivers_lake_centerlines")

def simplify_coords(coords, target_points=80):
    """Simplify coordinates using Douglas-Peucker-like approach."""
    if len(coords) <= target_points:
        return coords
    step = max(1, len(coords) // target_points)
    simplified = []
    for i in range(0, len(coords), step):
        simplified.append(coords[i])
    if simplified[-1] != coords[-1]:
        simplified.append(coords[-1])
    return simplified

def download_natural_earth():
    """Download and extract Natural Earth rivers shapefile."""
    zip_path = os.path.join(TEMP_DIR, "rivers.zip")
    
    if os.path.exists(SHAPEFILE_PATH + ".shp"):
        print("Using cached Natural Earth data")
        return
    
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    print("Downloading Natural Earth rivers...")
    urllib.request.urlretrieve(NATURAL_EARTH_URL, zip_path)
    
    print("Extracting...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(TEMP_DIR)

def extract_rivers():
    """Extract matching rivers from Natural Earth shapefile."""
    sf = shapefile.Reader(SHAPEFILE_PATH)
    fields = [field[0] for field in sf.fields[1:]]
    
    # Get all features with names, handling multi-part geometries
    features = []
    for record in sf.iterRecords():
        shape_idx = record.oid
        props = dict(zip(fields, record))
        shape = sf.shape(shape_idx)
        
        if shape.shapeType == 3:  # Polyline
            # Handle multi-part geometries by extracting the longest segment
            parts = shape.parts if hasattr(shape, 'parts') else []
            if len(parts) > 1:
                # Multiple segments - find the longest one
                segments = []
                for i in range(len(parts)):
                    start = parts[i]
                    end = parts[i+1] if i+1 < len(parts) else len(shape.points)
                    segment = shape.points[start:end]
                    segments.append(segment)
                # Use the longest segment
                longest = max(segments, key=len)
                features.append({'props': props, 'coords': longest})
            else:
                # Single segment
                coords = shape.points
                features.append({'props': props, 'coords': coords})
    
    # Match rivers
    matched = {}
    for target_name, search_terms in RIVER_SEARCH.items():
        for feature in features:
            name = feature['props'].get('name', '')
            for term in search_terms:
                if term.lower() in name.lower():
                    if target_name not in matched:
                        matched[target_name] = []
                    matched[target_name].append(feature)
                    break
    
    # Build GeoJSON
    geojson = {"type": "FeatureCollection", "features": []}
    
    for target_name, search_terms in RIVER_SEARCH.items():
        if target_name in matched:
            best = max(matched[target_name], key=lambda f: len(f['coords']))
            coords = [[p[0], p[1]] for p in best['coords']]
            coords = simplify_coords(coords)
            geojson["features"].append({
                "type": "Feature",
                "properties": {"name": target_name, "color": "#3B9BD6"},
                "geometry": {"type": "LineString", "coordinates": coords}
            })
            print(f"Matched: {target_name} ({len(coords)} points)")
        elif target_name in FALLBACK_RIVERS:
            geojson["features"].append({
                "type": "Feature",
                "properties": {"name": target_name, "color": "#3B9BD6"},
                "geometry": {"type": "LineString", "coordinates": FALLBACK_RIVERS[target_name]}
            })
            print(f"Using fallback: {target_name}")
        else:
            print(f"MISSING: {target_name}")
    
    return geojson

def main():
    download_natural_earth()
    geojson = extract_rivers()
    
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rivers.json")
    with open(output_path, "w") as f:
        json.dump(geojson, f, indent=2)
    
    print(f"\nSaved {len(geojson['features'])} rivers to rivers.json")

if __name__ == "__main__":
    main()

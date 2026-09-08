import sys
from pathlib import Path
import re
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lunarcv.config import OHRC_XML_PATH, LRO_IMG_PATH, OHRC_GEOM_CSV

def get_pds_val(text: str, key: str, default=None):
    m = re.search(rf"{key}\s*=\s*([^\r\n<]+)", text)
    if m:
        val_str = m.group(1).split("<")[0].strip().strip('"')
        return val_str
    return default

def check_metadata():
    print("--- Part 2: Metadata and Assumptions Verification ---")
    
    # 1. Orientation
    print("\n[Orientation Check]")
    if LRO_IMG_PATH.exists():
        with open(LRO_IMG_PATH, "rb") as f:
            lro_header = f.read(100000).decode("latin-1", errors="ignore")
        
        lro_proj = get_pds_val(lro_header, "MAP_PROJECTION_TYPE")
        lro_emission = get_pds_val(lro_header, "EMISSION_ANGLE")
        lro_fly = get_pds_val(lro_header, "SPACECRAFT_FLIGHT_DIRECTION")
        print(f"LRO NAC Map Projection: {lro_proj}")
        print(f"LRO NAC Flight Direction: {lro_fly}")
    else:
        print("LRO Image not found.")
        
    if OHRC_XML_PATH.exists():
        with open(OHRC_XML_PATH, "r") as f:
            ohrc_xml = f.read()
            # Simple grep for orientation if present
            if "orientation" in ohrc_xml.lower():
                print("OHRC XML contains orientation info.")
            else:
                print("OHRC XML does not explicitly state orientation, standard is North-Up.")
    else:
        print("OHRC XML not found.")

    # 2. Coordinate Convention & Linearity
    print("\n[Coordinate Convention and Linearity Check]")
    if OHRC_GEOM_CSV.exists():
        df = pd.read_csv(OHRC_GEOM_CSV)
        print(f"Loaded OHRC geometry CSV with {len(df)} points.")
        print(f"Columns: {df.columns.tolist()}")
        
        # Check Longitude Range
        lon_col = [c for c in df.columns if 'lon' in c.lower()][0]
        lat_col = [c for c in df.columns if 'lat' in c.lower()][0]
        row_col = [c for c in df.columns if 'row' in c.lower() or 'line' in c.lower() or 'scan' in c.lower()][0]
        
        min_lon, max_lon = df[lon_col].min(), df[lon_col].max()
        print(f"Longitude range in CSV: {min_lon:.4f} to {max_lon:.4f}")
        if min_lon < 0:
            print("Convention: -180 to 180")
        elif max_lon > 180:
            print("Convention: 0 to 360")
        else:
            print("Convention: Ambiguous (could be either, all values in 0-180)")
            
        # Check Linearity
        # Calculate Delta Lat per Delta Row
        df_scan = df.groupby(row_col)[lat_col].mean().reset_index()
        df_scan = df_scan.sort_values(by=row_col)
        df_scan['delta_row'] = df_scan[row_col].diff()
        df_scan['delta_lat'] = df_scan[lat_col].diff()
        df_scan['lat_per_row'] = df_scan['delta_lat'] / df_scan['delta_row']
        
        valid_rates = df_scan['lat_per_row'].dropna()
        mean_rate = valid_rates.mean()
        std_rate = valid_rates.std()
        cv_rate = std_rate / abs(mean_rate) if mean_rate != 0 else 0
        
        print(f"Mean Lat per Row: {mean_rate:.8f}")
        print(f"Std Dev Lat per Row: {std_rate:.8f} (CV: {cv_rate:.4%})")
        
        if cv_rate > 0.05:
            print("  WARNING: High variance in Lat per Row. Mapping is highly NON-LINEAR!")
        else:
            print("  Mapping appears mostly linear along-track.")
            
    else:
        print("OHRC GEOM CSV not found.")

if __name__ == "__main__":
    check_metadata()

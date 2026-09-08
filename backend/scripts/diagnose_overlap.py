import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lunarcv.config import (
    LRO_GSD, OHRC_GSD, SCALE_X_LRO_TO_OHRC, SCALE_Y_LRO_TO_OHRC
)

def diagnose_scale_and_overlap():
    print("--- Scale Mismatch Check ---")
    print(f"OHRC GSD: {OHRC_GSD} m/px")
    
    # Typical LRO NAC metrics
    lro_y_gsd = 1.66
    lro_x_gsd_summed = 1.55 * 2 # If summed cross-track
    lro_x_gsd_normal = 1.55
    
    expected_y_scale = lro_y_gsd / OHRC_GSD
    expected_x_scale_summed = lro_x_gsd_summed / OHRC_GSD
    expected_x_scale_normal = lro_x_gsd_normal / OHRC_GSD
    
    print(f"Configured SCALE_Y: {SCALE_Y_LRO_TO_OHRC:.2f}x")
    print(f"Theoretical SCALE_Y: {expected_y_scale:.2f}x")
    print(f"-> Y Error: {abs(SCALE_Y_LRO_TO_OHRC - expected_y_scale) / expected_y_scale:.2%}")
    
    print(f"Configured SCALE_X: {SCALE_X_LRO_TO_OHRC:.2f}x")
    print(f"Theoretical SCALE_X (summed): {expected_x_scale_summed:.2f}x")
    print(f"Theoretical SCALE_X (normal): {expected_x_scale_normal:.2f}x")
    
    if abs(SCALE_X_LRO_TO_OHRC - expected_x_scale_summed) < abs(SCALE_X_LRO_TO_OHRC - expected_x_scale_normal):
        x_err = abs(SCALE_X_LRO_TO_OHRC - expected_x_scale_summed) / expected_x_scale_summed
        print(f"-> X Error (vs summed): {x_err:.2%}")
    else:
        x_err = abs(SCALE_X_LRO_TO_OHRC - expected_x_scale_normal) / expected_x_scale_normal
        print(f"-> X Error (vs normal): {x_err:.2%}")

    print("\n--- Overlap Size Check ---")
    ohrc_crop_h, ohrc_crop_w = 15000, 6000
    lro_crop_h, lro_crop_w = 3000, 1400
    
    # If we scaled OHRC to LRO using theoretical scales (assuming LRO is normal, not summed, let's see)
    # LRO shape is 52224x2532. The width 2532 is standard NAC. Summed is typically 2532, unsummed is 5064.
    # So it IS summed (2x binning).
    
    ohrc_expected_lro_h = ohrc_crop_h / expected_y_scale
    ohrc_expected_lro_w = ohrc_crop_w / expected_x_scale_summed
    
    print(f"OHRC crop: {ohrc_crop_h}x{ohrc_crop_w}")
    print(f"OHRC crop converted to LRO pixels (theoretical scale): {ohrc_expected_lro_h:.0f}x{ohrc_expected_lro_w:.0f}")
    print(f"LRO crop provided in script: {lro_crop_h}x{lro_crop_w}")
    
    # Matcher receives:
    ohrc_scaled_h = ohrc_crop_h / SCALE_Y_LRO_TO_OHRC
    ohrc_scaled_w = ohrc_crop_w / SCALE_X_LRO_TO_OHRC
    print(f"\nMatcher currently receives:")
    print(f"OHRC Scaled: {ohrc_scaled_h:.0f}x{ohrc_scaled_w:.0f}")
    print(f"LRO Crop   : {lro_crop_h}x{lro_crop_w}")

if __name__ == "__main__":
    diagnose_scale_and_overlap()

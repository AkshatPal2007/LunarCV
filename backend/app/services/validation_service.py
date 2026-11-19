"""Header-based input validation without decoding full mission rasters."""

import warnings
from pathlib import Path

import rasterio
from rasterio.errors import NotGeoreferencedWarning

from app.config import settings


def validate_uploaded_file(file_path: Path, max_size_mb=2048):
    result = {"valid": False, "error": None, "warnings": [], "metadata": {}}
    if (
        not file_path.is_file()
        or file_path.suffix.lower() not in settings.ALLOWED_EXTENSIONS
    ):
        result["error"] = "Missing file or unsupported extension"
        return result
    size = file_path.stat().st_size
    if not 0 < size <= max_size_mb * 1024**2:
        result["error"] = "File is empty or exceeds upload limit"
        return result
    result["metadata"]["file_size"] = size
    if file_path.suffix.lower() == ".img":
        # PDS4 labels arrive separately under the immutable upload ID.
        result["warnings"].append(
            "IMG requires a valid attached PDS3 or uploaded PDS4 label before registration"
        )
    else:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", NotGeoreferencedWarning)
                with rasterio.open(file_path) as data:
                    if min(data.width, data.height) < 64:
                        raise ValueError("Image must be at least 64x64 pixels")
                    result["metadata"]["dimensions"] = (data.height, data.width)
        except Exception as exc:
            result["error"] = f"Cannot read image header: {exc}"
            return result
    result["valid"] = True
    return result


def validate_registration_pair(source_path, ref_path):
    for path in (source_path, ref_path):
        result = validate_uploaded_file(Path(path), settings.MAX_UPLOAD_SIZE // 1024**2)
        if not result["valid"]:
            return result
        if Path(path).suffix.lower() == ".img":
            try:
                from lunarcv.io.raster import load_pds_memmap

                raster, _ = load_pds_memmap(Path(path))
                del raster
            except Exception as exc:
                return {"valid": False, "error": str(exc), "warnings": []}
    return {"valid": True, "error": None, "warnings": []}

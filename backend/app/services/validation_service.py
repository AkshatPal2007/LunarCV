"""Validation service for image files and registration pairs."""

from pathlib import Path

import cv2

from app.config import settings


class ValidationError(Exception):
    """User-facing validation error."""

    pass


def validate_uploaded_file(file_path: Path, max_size_mb: int = 1024) -> dict[str, any]:
    """
    Validate file before accepting upload.

    Checks: exists, extension allowed, size limit, can be opened, valid dimensions.
    Returns: {valid: bool, error: str or None, warnings: list, metadata: dict}
    """
    warnings = []
    metadata = {}

    # Check file exists
    if not file_path.exists():
        return {"valid": False, "error": "File does not exist", "warnings": warnings}

    # Check extension
    if file_path.suffix.lower() not in settings.ALLOWED_EXTENSIONS:
        return {
            "valid": False,
            "error": f"Invalid file type. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}",
            "warnings": warnings,
        }

    # Check file size
    file_size = file_path.stat().st_size
    max_size_bytes = max_size_mb * 1024 * 1024

    if file_size > max_size_bytes:
        return {
            "valid": False,
            "error": f"File too large. Max size: {max_size_mb}MB",
            "warnings": warnings,
        }

    metadata["file_size"] = file_size

    # Try to open as image for basic format check
    try:
        # For .img files, we can't use cv2.imread() reliably, so skip this check
        if file_path.suffix.lower() not in [".img"]:
            img = cv2.imread(str(file_path), cv2.IMREAD_GRAYSCALE)
            if img is not None:
                h, w = img.shape
                metadata["dimensions"] = (h, w)

                # Check for valid dimensions
                if h <= 0 or w <= 0:
                    return {
                        "valid": False,
                        "error": "Image has invalid dimensions",
                        "warnings": warnings,
                    }

                # Warn about very large images
                if h > 100000 or w > 100000:
                    warnings.append(
                        f"Large image ({h}x{w}px) - patch extraction will be applied"
                    )

    except Exception as e:
        # For .img files or if cv2 fails, this is not necessarily an error
        # The image_loader will handle these cases properly
        if file_path.suffix.lower() not in [".img"]:
            warnings.append(f"Could not validate image format: {e}")

    return {
        "valid": True,
        "error": None,
        "warnings": warnings,
        "metadata": metadata,
    }


def validate_registration_pair(
    source_path: Path, ref_path: Path
) -> dict[str, str | None | list[str]]:
    """
    Validate image pair before job creation.

    Checks: both valid, compatible formats, reasonable dimension ratios, not too small.
    Returns: {valid: bool, error: str or None, warnings: list}
    """
    warnings = []

    # Validate both files exist
    if not source_path.exists():
        return {
            "valid": False,
            "error": f"Source image not found: {source_path.name}",
            "warnings": warnings,
        }

    if not ref_path.exists():
        return {
            "valid": False,
            "error": f"Reference image not found: {ref_path.name}",
            "warnings": warnings,
        }

    # Get file sizes
    source_size = source_path.stat().st_size
    ref_size = ref_path.stat().st_size

    # Check minimum file size (likely corrupted if smaller than 1KB)
    if source_size < 1024:
        return {
            "valid": False,
            "error": f"Source image file is too small ({source_size} bytes) - possibly corrupted",
            "warnings": warnings,
        }

    if ref_size < 1024:
        return {
            "valid": False,
            "error": f"Reference image file is too small ({ref_size} bytes) - possibly corrupted",
            "warnings": warnings,
        }

    # Try to get dimensions for standard formats
    try:
        source_ext = source_path.suffix.lower()
        ref_ext = ref_path.suffix.lower()

        # Skip dimension checks for .img files since cv2.imread() can't read them
        if source_ext not in [".img"] and ref_ext not in [".img"]:
            source_img = cv2.imread(str(source_path), cv2.IMREAD_GRAYSCALE)
            ref_img = cv2.imread(str(ref_path), cv2.IMREAD_GRAYSCALE)

            if source_img is not None and ref_img is not None:
                sh, sw = source_img.shape
                rh, rw = ref_img.shape

                # Check for very small images
                if sh < 64 or sw < 64:
                    return {
                        "valid": False,
                        "error": f"Source image too small ({sh}x{sw}px) - need at least 64x64px",
                        "warnings": warnings,
                    }

                if rh < 64 or rw < 64:
                    return {
                        "valid": False,
                        "error": f"Reference image too small ({rh}x{rw}px) - need at least 64x64px",
                        "warnings": warnings,
                    }

                # Warn about large size mismatches (might indicate wrong image pair)
                size_ratio = max(sh * sw, rh * rw) / min(sh * sw, rh * rw)
                if size_ratio > 100:
                    warnings.append(
                        f"Large size difference between images (ratio: {size_ratio:.1f}x) - verify this is the correct pair"
                    )

    except Exception:
        # If we can't validate dimensions, that's okay - the image_loader will handle it
        pass

    return {"valid": True, "error": None, "warnings": warnings}

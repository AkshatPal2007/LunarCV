"""
io_utils.py — Zero-copy memory mapping and PDS header parsing for LunarCV.

Supports:
    - Chandrayaan-2 OHRC (90148 x 12000 uint8, PDS4)
    - Chandrayaan-2 TMC-2 (148108 x 4000 uint16, PDS4)
    - NASA LRO NAC (e.g. M1350459544RE, M1529041271LE, PDS3)
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
from defusedxml import ElementTree


def load_ohrc_memmap(
    img_path: Path,
    shape: tuple[int, int] = (90148, 12000),
    dtype: str = "uint8",
    offset: int = 0,
) -> np.memmap:
    """Open Chandrayaan-2 OHRC .img file via zero-copy np.memmap."""
    return np.memmap(img_path, dtype=dtype, mode="r", offset=offset, shape=shape)


def load_tmc2_memmap(
    img_path: Path,
    shape: tuple[int, int] = (148108, 4000),
    dtype: str = "uint16",
    offset: int = 0,
) -> np.memmap:
    """Open Chandrayaan-2 TMC-2 .img file via zero-copy np.memmap."""
    return np.memmap(img_path, dtype=dtype, mode="r", offset=offset, shape=shape)


def parse_lro_pds_header(img_path: Path) -> dict:
    """Parse key PDS3 label attributes from LRO NAC .IMG header."""
    with open(img_path, "rb") as f:
        header_text = f.read(100000).decode("latin-1", errors="ignore")

    def get_val(key: str, default=None, cast=str):
        m = re.search(rf"{key}\s*=\s*([^\r\n<]+)", header_text)
        if m:
            val_str = m.group(1).split("<")[0].strip().strip('"')
            try:
                return cast(val_str)
            except Exception:
                return val_str
        return default

    rec_bytes = get_val("RECORD_BYTES", cast=int)
    lbl_recs = get_val("LABEL_RECORDS", cast=int)
    lines = get_val("LINES", cast=int)
    samples = get_val("LINE_SAMPLES", cast=int)
    bits = get_val("SAMPLE_BITS", cast=int)

    # Offset is always LABEL_RECORDS * RECORD_BYTES in standard PDS3
    image_pointer = get_val(r"\^IMAGE", cast=int)
    offset = ((image_pointer - 1) * rec_bytes) if image_pointer and rec_bytes else 0
    sample_type = get_val("SAMPLE_TYPE", default="MSB_INTEGER").upper()
    byte_order = "little" if "LSB" in sample_type else "big"
    dtype = np.dtype(("<" if byte_order == "little" else ">") + ("u1" if bits == 8 else "u2"))

    return {
        "record_bytes": rec_bytes,
        "label_records": lbl_recs,
        "lines": lines,
        "line_samples": samples,
        "sample_bits": bits,
        "offset": offset,
        "dtype": dtype,
        "byte_order": byte_order,
        "shape": (lines, samples) if (lines and samples) else None,
    }


def load_lro_nac_memmap(img_path: Path) -> tuple[np.memmap, dict]:
    """Open LRO NAC .IMG file via np.memmap using header metadata."""
    meta = parse_lro_pds_header(img_path)
    if not meta["shape"]:
        raise ValueError(f"Could not parse shape from header of {img_path}")
    arr = np.memmap(
        img_path,
        dtype=meta["dtype"],
        mode="r",
        offset=meta["offset"],
        shape=meta["shape"],
    )
    return arr, meta


def _xml_value(root: ElementTree.Element, local_name: str) -> str | None:
    """Find a PDS4 XML element by local name, ignoring namespaces."""
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] == local_name and element.text:
            return element.text.strip()
    return None


def parse_pds4_xml(img_path: Path) -> dict:
    """Parse the image fields needed for a PDS4 detached-label product."""
    label_path = img_path.with_suffix(".xml")
    if not label_path.exists():
        raise ValueError(f"PDS4 label not found next to {img_path.name}: {label_path.name}")

    root = ElementTree.parse(label_path).getroot()

    def required(name: str) -> str:
        value = _xml_value(root, name)
        if value is None:
            raise ValueError(f"PDS4 label {label_path.name} is missing {name}")
        return value

    axis_sizes: dict[str, int] = {}
    for axis in root.iter():
        if axis.tag.rsplit("}", 1)[-1] != "Axis_Array":
            continue
        axis_name = _xml_value(axis, "axis_name")
        elements = _xml_value(axis, "elements")
        if axis_name and elements:
            axis_sizes[axis_name.lower()] = int(elements)
    if "line" not in axis_sizes or "sample" not in axis_sizes:
        raise ValueError(f"PDS4 label {label_path.name} must define Line and Sample axes")
    lines = axis_sizes["line"]
    samples = axis_sizes["sample"]
    offset = int(_xml_value(root, "offset") or "0")
    data_type = (_xml_value(root, "data_type") or "UnsignedByte").upper()
    bits_selection = (_xml_value(root, "bits_selection") or "MSB").upper()
    byte_order = "little" if "LSB" in bits_selection or "LITTLE" in bits_selection else "big"
    if data_type in {"UNSIGNEDBYTE", "SIGNEDBYTE"}:
        dtype_code = "u1"
    elif data_type in {"UNSIGNEDMSB2", "UNSIGNEDLSB2", "SIGNEDMSB2", "SIGNEDLSB2"}:
        dtype_code = "u2" if "UNSIGNED" in data_type else "i2"
    elif data_type in {"UNSIGNEDMSB4", "UNSIGNEDLSB4", "SIGNEDMSB4", "SIGNEDLSB4"}:
        dtype_code = "u4" if "UNSIGNED" in data_type else "i4"
    else:
        raise ValueError(f"Unsupported PDS4 data type: {data_type}")
    bits = np.dtype(dtype_code).itemsize * 8

    return {
        "label_path": str(label_path),
        "offset": offset,
        "dtype": np.dtype(("<" if byte_order == "little" else ">") + dtype_code),
        "byte_order": byte_order,
        "shape": (lines, samples),
        "sample_bits": bits,
    }


def load_pds_memmap(img_path: Path) -> tuple[np.memmap, dict]:
    """Load PDS3 or PDS4 imagery using the product's declared metadata."""
    with img_path.open("rb") as handle:
        prefix = handle.read(256).decode("latin-1", errors="ignore")

    if "PDS_VERSION_ID" in prefix:
        meta = parse_lro_pds_header(img_path)
    else:
        meta = parse_pds4_xml(img_path)

    if not meta.get("shape") or any(value <= 0 for value in meta["shape"]):
        raise ValueError(f"Invalid image shape in label for {img_path.name}")

    rows, columns = meta["shape"]
    item_bytes = meta["dtype"].itemsize
    required_bytes = meta["offset"] + rows * columns * item_bytes
    actual_bytes = img_path.stat().st_size
    if actual_bytes < required_bytes:
        raise ValueError(
            f"{img_path.name} is truncated: need {required_bytes} bytes, found {actual_bytes}"
        )

    return np.memmap(
        img_path,
        dtype=meta["dtype"],
        mode="r",
        offset=meta["offset"],
        shape=(rows, columns),
    ), meta


def extract_patch(
    memmap_array: np.memmap, row_range: tuple[int, int], col_range: tuple[int, int]
) -> np.ndarray:
    """Extract a patch from a memmapped array as an in-memory numpy array copy."""
    r0, r1 = row_range
    c0, c1 = col_range
    return memmap_array[r0:r1, c0:c1].copy()


def print_patch_stats(patch: np.ndarray, label: str = "patch") -> None:
    """Print summary statistics for an image patch."""
    print(f"--- {label} stats ---")
    print(f"shape : {patch.shape}")
    print(f"dtype : {patch.dtype}")
    print(f"min   : {patch.min()}")
    print(f"max   : {patch.max()}")
    sample = patch[::4, ::4].astype(np.float32)
    print(f"mean  : {sample.mean():.4f}")
    print(f"std   : {sample.std():.4f}")

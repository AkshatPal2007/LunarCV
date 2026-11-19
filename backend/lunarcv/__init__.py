"""LunarCV public helpers; heavy inference dependencies load only when used."""

from importlib import import_module

__version__ = "0.3.0"
_EXPORTS = {
    "RegistrationMetrics": ("evaluation.metrics", "RegistrationMetrics"),
    "calculate_rmse": ("evaluation.metrics", "calculate_rmse"),
    "evaluate_spatial_uniformity": (
        "evaluation.metrics",
        "evaluate_spatial_uniformity",
    ),
    "quality_gate": ("evaluation.metrics", "quality_gate"),
    "compute_overlap": ("geo.geo_prior", "compute_overlap"),
    "estimate_scale_ratio": ("geo.geo_prior", "estimate_scale_ratio"),
    "generate_tiles": ("geo.geo_prior", "generate_tiles"),
    "BoundingBox": ("geo.metadata", "BoundingBox"),
    "ImageMetadata": ("geo.metadata", "ImageMetadata"),
    "extract_patch": ("io.raster", "extract_patch"),
    "load_lro_nac_memmap": ("io.raster", "load_lro_nac_memmap"),
    "load_ohrc_memmap": ("io.raster", "load_ohrc_memmap"),
    "EnsembleMatcher": ("matching.ensemble", "EnsembleMatcher"),
    "LightGlueFeatureMatcher": (
        "matching.lightglue_matcher",
        "LightGlueFeatureMatcher",
    ),
    "Matcher": ("matching.matcher", "Matcher"),
    "magsac_filter": ("registration.outlier_rejection", "magsac_filter"),
    "compute_registration": ("registration.transform", "compute_registration"),
    "RegistrationEngine": ("engine", "RegistrationEngine"),
    "RegistrationConfig": ("settings", "RegistrationConfig"),
}
__all__ = list(_EXPORTS)


def __getattr__(name):
    if name not in _EXPORTS:
        raise AttributeError(name)
    module, attribute = _EXPORTS[name]
    value = getattr(import_module(f"lunarcv.{module}"), attribute)
    globals()[name] = value
    return value

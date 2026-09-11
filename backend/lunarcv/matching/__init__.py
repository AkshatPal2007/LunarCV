"""lunarcv.matching — Feature matching backends."""

from lunarcv.matching.ensemble import EnsembleMatcher
from lunarcv.matching.lightglue_matcher import LightGlueFeatureMatcher
from lunarcv.matching.matcher import Matcher

# RIFT2 is optional (requires third_party/rift2 to be present)
try:
    from lunarcv.matching.rift2_matcher import RIFT2Matcher

    __all__ = ["Matcher", "LightGlueFeatureMatcher", "EnsembleMatcher", "RIFT2Matcher"]
except ImportError:
    __all__ = ["Matcher", "LightGlueFeatureMatcher", "EnsembleMatcher"]
from .adaptive import adaptive_chunked_match as adaptive_chunked_match

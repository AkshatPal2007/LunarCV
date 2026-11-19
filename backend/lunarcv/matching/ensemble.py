"""Parallel agreement-aware fusion. Scores rank support, not probabilities."""

import logging
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from scipy.spatial import cKDTree

from lunarcv.matching.matcher import Matcher

logger = logging.getLogger(__name__)


class EnsembleMatcher(Matcher):
    def __init__(self, matchers, agreement_radius=3.0):
        if not matchers:
            raise ValueError("At least one matcher is required")
        self.matchers = matchers
        self.agreement_radius = agreement_radius
        self.diagnostics = {}
        self.secondary_enabled = True

    def reset_run(self):
        """Adaptive fallback is per run, never carried into another scene."""
        self.secondary_enabled = True
        self.diagnostics = {}

    def match(self, src_img, ref_img, conf_threshold=0.0):
        durations = {}

        def call(matcher):
            started = time.perf_counter()
            try:
                return matcher.match(src_img, ref_img, conf_threshold), None
            except Exception as exc:
                logger.warning("Matcher %s failed: %s", type(matcher).__name__, exc)
                return None, str(exc)
            finally:
                durations[type(matcher).__name__] = round(
                    time.perf_counter() - started, 6
                )

        active = self.matchers if self.secondary_enabled else self.matchers[:1]
        with ThreadPoolExecutor(max_workers=len(active)) as pool:
            results = list(pool.map(call, active))
        self.diagnostics = {
            type(m).__name__: {"count": len(r[0]) if r else 0, "error": e}
            for m, (r, e) in zip(active, results, strict=True)
        }
        self.diagnostics["matcher_wall_seconds"] = durations
        if len(active) > 1 and not any(
            result is not None and len(result[0]) for result, _ in results[1:]
        ):
            self.secondary_enabled = False
            self.diagnostics["secondary_fallback"] = (
                "No coarse-window candidates; skip secondary on remaining guided tiles in this run"
            )
        elif len(active) == 1 and len(self.matchers) > 1:
            self.diagnostics["secondary_fallback"] = (
                "Skipped after empty coarse-window result"
            )
        self.diagnostics["matcher_wall_seconds"] = durations
        primary, error = results[0]
        if primary is None:
            raise RuntimeError(f"Primary matcher failed: {error}")
        src, ref, confidence = primary
        support = np.zeros(len(src), dtype=bool)
        if len(src):
            for secondary, _ in results[1:]:
                if secondary is None or not len(secondary[0]):
                    continue
                # Both endpoints must agree; a nearby source alone is insufficient.
                neighbors = cKDTree(secondary[0]).query_ball_point(
                    src, self.agreement_radius
                )
                for i, candidates in enumerate(neighbors):
                    if candidates and np.any(
                        np.linalg.norm(secondary[1][candidates] - ref[i], axis=1)
                        <= self.agreement_radius
                    ):
                        support[i] = True
        self.diagnostics["agreed_matches"] = int(support.sum())
        self.diagnostics["policy"] = (
            "primary_with_agreement_priority; primary_only_when_secondary_fails"
        )
        # Keep primary probabilities separately: callers can decode the +1 support tier.
        return src, ref, confidence.astype(np.float32) + support.astype(np.float32)

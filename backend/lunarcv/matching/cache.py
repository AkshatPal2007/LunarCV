"""Numeric-only, content-addressed match cache. Corruption is a cache miss."""

import hashlib
import json
import os
import tempfile
from pathlib import Path

import numpy as np

CACHE_VERSION = 1


def cache_key(identity):
    return hashlib.sha256(
        json.dumps(identity, sort_keys=True, allow_nan=False).encode()
    ).hexdigest()


def load_matches(path, identity):
    try:
        with np.load(path, allow_pickle=False) as data:
            if (
                json.loads(str(data["identity"])) != identity
                or int(data["version"]) != CACHE_VERSION
            ):
                return None
            src, ref, scores = (
                data[name].copy() for name in ("source", "reference", "scores")
            )
            if (
                src.shape != ref.shape
                or src.ndim != 2
                or src.shape[1] != 2
                or scores.shape != (len(src),)
            ):
                return None
            if not all(np.isfinite(a).all() for a in (src, ref, scores)):
                return None
            return src, ref, scores, json.loads(str(data["diagnostics"]))
    except (OSError, ValueError, KeyError, EOFError):
        return None


def save_matches(path, identity, source, reference, scores, diagnostics):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, suffix=".npz")
    try:
        with os.fdopen(fd, "wb") as handle:
            np.savez_compressed(
                handle,
                version=CACHE_VERSION,
                identity=json.dumps(identity, sort_keys=True),
                source=source,
                reference=reference,
                scores=scores,
                diagnostics=json.dumps(diagnostics, allow_nan=False),
            )
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)

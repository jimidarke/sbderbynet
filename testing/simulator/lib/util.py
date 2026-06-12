"""Shared helpers for the race simulator: logging, constants, json io."""

import json
import logging
import os
import sys

DNF_TIME = 99.999
# Two aggregate scores within this epsilon are "the same score" for tie
# purposes.  Mirrors ELIMINATION_SCORE_EPSILON in website/inc/elimination-config.inc.
SCORE_EPSILON = 0.0005

TENANT_SLUG_RE = r"^sim-\d+$"
OFFICIAL_TENANT = "st-albert-2026-official"


def make_logger(name: str, verbose: bool = False) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)-7s %(name)s: %(message)s", "%H:%M:%S"))
        logger.addHandler(handler)
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    return logger


def load_json(path: str):
    with open(path) as f:
        return json.load(f)


def save_json(path: str, data) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")


def find_configs_dir() -> str:
    """Locate the elimination-config JSON directory.  In a deployed
    container it's mounted at /configs; in the repo it's relative."""
    env = os.getenv("SIM_CONFIGS_DIR")
    candidates = [env] if env else []
    here = os.path.dirname(os.path.abspath(__file__))
    candidates += [
        "/configs",
        os.path.normpath(os.path.join(
            here, "..", "..", "..", "website", "inc", "elimination-configs")),
    ]
    for c in candidates:
        if c and os.path.isdir(c):
            return c
    raise RuntimeError("cannot locate elimination-configs dir; set SIM_CONFIGS_DIR")


def t3(value: float) -> float:
    """Quantize a time to the 3-decimal resolution the track records at."""
    return round(float(value), 3)


def is_dnf(value) -> bool:
    return value is not None and float(value) >= DNF_TIME - SCORE_EPSILON


def scores_equal(a: float, b: float) -> bool:
    return abs(float(a) - float(b)) <= SCORE_EPSILON

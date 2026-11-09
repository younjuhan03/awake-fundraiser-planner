"""Load config/assumptions.yaml."""
from __future__ import annotations

import yaml

from .paths import CONFIG

CONFIDENCE_LEVELS = ("observed", "derived", "assumed")


def load_raw(path=CONFIG) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def scalar_assumptions(path=CONFIG) -> dict:
    """Entries with a single `value` (everything except the price schedule)."""
    return {k: v for k, v in load_raw(path).items() if "value" in v}


def values(path=CONFIG) -> dict:
    return {k: v["value"] for k, v in scalar_assumptions(path).items()}


def price_schedule(path=CONFIG) -> dict:
    return {int(q): float(p) for q, p in load_raw(path)["price_schedule"]["table"].items()}

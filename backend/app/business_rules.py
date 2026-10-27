"""Canonical business rules shared by ETL, dashboards and model training."""

from __future__ import annotations

from datetime import date
from typing import Any

EARLY_WINDOW_DAYS = 180
VOLUNTARY_EXIT_TYPES = {
    "voluntary",
    "renuncia",
    "resignation",
    "retiro voluntario",
}
INVOLUNTARY_EXIT_TYPES = {
    "involuntary",
    "despido",
    "terminacion",
    "terminación",
    "dismissal",
    "fired",
}


def early_resignation_label(
    hire_date: date | None,
    exit_date: date | None,
    exit_type: Any,
    as_of_date: date,
) -> int | None:
    """Return 1 for voluntary exit in days 1–180, 0 if fully observed, else None."""
    if hire_date is None or hire_date > as_of_date:
        return None
    if exit_date is not None and exit_date < hire_date:
        return None
    normalized = str(exit_type or "").strip().lower()
    days = (exit_date - hire_date).days if exit_date else (as_of_date - hire_date).days
    if normalized in VOLUNTARY_EXIT_TYPES and exit_date is not None and days <= EARLY_WINDOW_DAYS:
        return 1
    if normalized in INVOLUNTARY_EXIT_TYPES and exit_date is not None and days < EARLY_WINDOW_DAYS:
        return None
    if days >= EARLY_WINDOW_DAYS:
        return 0
    return None

import pandas as pd

from backend.app.analytics import _supervisors, apply_filters


def test_supervisor_groups_below_threshold_are_not_listed_or_filterable():
    frame = pd.DataFrame(
        {
            "hire_month": ["2026-01"] * 19,
            "campaign": ["A"] * 19,
            "shift": ["day"] * 19,
            "supervisor": ["Unique supervisor"] * 19,
            "early_resignation": [1] * 7 + [0] * 12,
        }
    )

    assert _supervisors(frame) == []
    assert apply_filters(frame, supervisor="Unique supervisor").empty

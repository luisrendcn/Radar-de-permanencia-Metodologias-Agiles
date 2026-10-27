from datetime import date, timedelta

import pytest

from backend.app.business_rules import early_resignation_label


AS_OF = date(2026, 10, 20)


@pytest.mark.parametrize(
    ("hire_day", "exit_day", "exit_type", "expected"),
    [
        (date(2026, 1, 1), date(2026, 3, 1), "voluntary", 1),
        (date(2026, 1, 1), date(2026, 6, 30), "renuncia", 1),
        (date(2026, 1, 1), date(2026, 7, 1), "voluntary", 0),
        (date(2026, 1, 1), None, "", 0),
        (date(2026, 7, 1), None, "", None),
        (date(2026, 1, 1), date(2026, 2, 1), "involuntary", None),
        (date(2026, 1, 1), date(2026, 1, 1) - timedelta(days=1), "voluntary", None),
    ],
)
def test_early_resignation_label(hire_day, exit_day, exit_type, expected):
    assert early_resignation_label(hire_day, exit_day, exit_type, AS_OF) == expected


def test_follow_up_on_day_180_is_mature():
    hire_day = AS_OF - timedelta(days=180)
    assert early_resignation_label(hire_day, None, None, AS_OF) == 0

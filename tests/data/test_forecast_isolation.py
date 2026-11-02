"""Generic synthetic boundary dates only; no actual held-out allocation."""

from datetime import date

import pytest

from dc_sustainability.data.forecast_isolation import conflicts, footprint


def test_empty_window_set_cannot_pass_isolation():
    with pytest.raises(ValueError, match="window sets"):
        conflicts([], [date(2022, 1, 16)], history_hours=24, convention="start")


@pytest.mark.parametrize("convention", ["start", "end"])
@pytest.mark.parametrize("reverse", [False, True])
def test_history_leak_detected_even_when_scoring_windows_are_disjoint(convention, reverse):
    a, b = [date(2022, 1, 14)], [date(2022, 1, 16)]
    if reverse:
        a, b = b, a
    assert not conflicts(a, b, history_hours=0, convention=convention)
    assert conflicts(a, b, history_hours=24, convention=convention)


@pytest.mark.parametrize("convention", ["start", "end"])
def test_month_edge_and_separated_windows(convention):
    assert conflicts(
        [date(2022, 1, 31)], [date(2022, 2, 1)], history_hours=1, convention=convention
    )
    assert not conflicts(
        [date(2022, 1, 14)], [date(2022, 2, 16)], history_hours=24, convention=convention
    )


@pytest.mark.parametrize("day,history", [(date(2022, 1, 1), 24), (date(2022, 12, 31), 0)])
@pytest.mark.parametrize("convention", ["start", "end"])
def test_year_boundaries_fail_instead_of_wrapping(day, history, convention):
    with pytest.raises(ValueError, match="available year"):
        footprint(day, history_hours=history, convention=convention)

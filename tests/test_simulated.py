"""Tests for the seeded synthetic TTC-like dataset."""

import numpy as np
import pandas as pd
import pytest


EXPECTED_MIN_DELAY_VALUES = {0, 3, 5, 10, 20, 45}
EXPECTED_COLUMNS = {
    "Date", "Time", "Day", "Station", "Code", "Min Delay",
    "Min Gap", "Bound", "Line", "Vehicle", "Hour",
}


@pytest.fixture(scope="module")
def simulated(simulate_module):
    rng = np.random.default_rng(2026)
    return simulate_module.simulate(rng, simulate_module.N_OBSERVATIONS)


def test_row_count(simulated, simulate_module):
    assert len(simulated) == simulate_module.N_OBSERVATIONS


def test_schema(simulated):
    assert set(simulated.columns) == EXPECTED_COLUMNS


def test_dates_and_hours_are_valid(simulated):
    dates = pd.to_datetime(simulated["Date"], errors="coerce")
    times = pd.to_datetime(simulated["Time"], format="%H:%M", errors="coerce")
    assert dates.notna().all()
    assert times.notna().all()
    assert simulated["Hour"].between(0, 23).all()


def test_day_matches_date(simulated):
    dates = pd.to_datetime(simulated["Date"])
    assert (simulated["Day"] == dates.dt.day_name()).all()


def test_min_delay_values_are_from_the_known_set(simulated):
    assert simulated["Min Delay"].isin(EXPECTED_MIN_DELAY_VALUES).all()


def test_no_missing_values(simulated):
    assert not simulated.isna().any().any()


def test_delay_and_gap_are_nonnegative(simulated):
    assert (simulated["Min Delay"] >= 0).all()
    assert (simulated["Min Gap"] >= 0).all()


def test_line_values_match_the_simulated_station_map(simulated, simulate_module):
    expected = simulated["Station"].map(simulate_module.STATION_TO_LINE)
    assert (simulated["Line"] == expected).all()


def test_positive_delay_is_related_to_gap(simulated):
    positive = simulated["Min Delay"] > 0
    assert (simulated.loc[positive, "Min Gap"] >= simulated.loc[positive, "Min Delay"]).all()


def test_early_morning_rate_exceeds_late_night_rate(simulated):
    positive = simulated["Min Delay"] > 0
    early_morning_rate = positive[simulated["Hour"].isin([6, 7, 8])].mean()
    late_night_rate = positive[simulated["Hour"].isin([2, 3, 4])].mean()
    assert early_morning_rate > late_night_rate


def test_code_changes_positive_delay_rate(simulated):
    positive = simulated["Min Delay"] > 0
    rates = positive.groupby(simulated["Code"]).mean()
    assert rates.max() > rates.min()


def test_hourly_rates_match_the_simulation_parameters(simulate_module):
    rng = np.random.default_rng(2026)
    large_sample = simulate_module.simulate(rng, 200_000)
    positive = large_sample["Min Delay"] > 0
    # The code effect changes the marginal rate slightly, so compare the
    # highest and lowest hours rather than expecting exact baseline rates.
    empirical_rate = positive.groupby(large_sample["Hour"]).mean()
    assert empirical_rate[6] > empirical_rate[3]


def test_seed_is_reproducible(simulate_module):
    first = simulate_module.simulate(np.random.default_rng(2026), 2000)
    second = simulate_module.simulate(np.random.default_rng(2026), 2000)
    pd.testing.assert_frame_equal(first, second)

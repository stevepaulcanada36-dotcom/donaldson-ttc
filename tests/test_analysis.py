"""Deterministic tests for the statistical helper functions."""

import numpy as np
import pandas as pd
import pytest


def test_wilson_interval_contains_observed_rate(analysis_module):
    successes = pd.Series([50])
    observations = pd.Series([100])
    low, high = analysis_module.wilson_interval(successes, observations)
    assert 0 <= low.iloc[0] < 0.5 < high.iloc[0] <= 1


def test_wilson_interval_handles_extreme_counts(analysis_module):
    low, high = analysis_module.wilson_interval(pd.Series([0, 100]), pd.Series([100, 100]))
    assert low.tolist()[0] >= 0
    assert high.tolist()[1] <= 1
    assert low.tolist()[0] < high.tolist()[0]
    assert low.tolist()[1] < high.tolist()[1]


def test_cramers_v_is_zero_for_independence(analysis_module):
    table = pd.DataFrame([[25, 25], [25, 25]])
    assert analysis_module.cramers_v(table) == pytest.approx(0.0)


def test_cramers_v_is_one_for_perfect_binary_association(analysis_module):
    table = pd.DataFrame([[50, 0], [0, 50]])
    assert analysis_module.cramers_v(table) == pytest.approx(1.0)


def test_hourly_summary_has_all_hours(analysis_module, clean_module):
    rng = np.random.default_rng(2026)
    rows = []
    for hour in range(24):
        for _ in range(5):
            rows.append({
                "Hour": hour,
                "Min Delay": 5 if hour % 2 == 0 else 0,
                "Positive Delay": hour % 2 == 0,
                "Positive Delay Minutes": 5 if hour % 2 == 0 else np.nan,
            })
    data = pd.DataFrame(rows)
    hourly = analysis_module.summarize_hourly(data)
    assert hourly["Hour"].tolist() == list(range(24))
    assert hourly["observations"].sum() == len(data)
    assert hourly["rate_ci_low_percent"].between(0, 100).all()
    assert hourly["rate_ci_high_percent"].between(0, 100).all()

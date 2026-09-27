"""Tests for the real-data cleaning and analysis pipeline.

Run with: uv run pytest tests/test_actual.py -v

Requires data/raw_data/TTC_Subway_Delay_Data_since_2025.csv to already
exist (i.e. scripts/02_download_data.py has been run). Kept separate from
test_simulated.py so the simulated and real datasets are validated
independently, as required by the assignment rubric.
"""

import pandas as pd
import pytest


REQUIRED_RAW_COLUMNS = {
    "Date", "Time", "Day", "Station", "Code",
    "Min Delay", "Min Gap", "Bound", "Line", "Vehicle",
}


@pytest.fixture(scope="module")
def raw(clean_module):
    return pd.read_csv(clean_module.RAW_DATA_PATH)


@pytest.fixture(scope="module")
def cleaned(clean_module, raw):
    return clean_module.prepare_data(raw)


@pytest.fixture(scope="module")
def analyzed(analysis_module, cleaned):
    return analysis_module.analyze(cleaned)


# --- Structure: required columns exist -----------------------------------

def test_required_raw_columns_are_present(raw):
    assert REQUIRED_RAW_COLUMNS.issubset(set(raw.columns))


def test_raw_data_is_not_empty(raw):
    assert len(raw) > 0


def test_raw_date_and_time_fields_are_parseable(raw):
    parsed_date = pd.to_datetime(raw["Date"], errors="coerce")
    parsed_time = pd.to_datetime(raw["Time"], format="%H:%M", errors="coerce")
    assert parsed_date.notna().all()
    assert parsed_time.notna().all()


def test_cleaned_data_has_derived_columns(cleaned):
    expected = {"Hour", "Day", "Month", "Positive Delay", "Positive Delay Minutes"}
    assert expected.issubset(set(cleaned.columns))


# --- Types -----------------------------------------------------------------

def test_hour_is_integer(cleaned):
    assert cleaned["Hour"].dtype.kind in "iu"


def test_min_delay_is_numeric(cleaned):
    assert pd.api.types.is_numeric_dtype(cleaned["Min Delay"])


def test_date_is_datetime(cleaned):
    assert pd.api.types.is_datetime64_any_dtype(cleaned["Date"])


def test_positive_delay_is_boolean(cleaned):
    assert cleaned["Positive Delay"].dtype == bool


# --- Valid ranges ------------------------------------------------------------

def test_hour_range(cleaned):
    assert cleaned["Hour"].between(0, 23).all()


def test_min_delay_never_negative(cleaned):
    assert (cleaned["Min Delay"] >= 0).all()


# --- Categories --------------------------------------------------------------

def test_line_values_are_recognized_or_flagged(cleaned, analysis_module):
    """Every non-missing Line value is classified as either a recognized
    subway line or an anomaly; nothing falls through uncategorized."""
    classification = cleaned["Line"].apply(analysis_module.is_clean_subway_line)
    non_missing = cleaned["Line"].notna()
    assert classification[non_missing].isin([True, False]).all()


def test_day_values_are_valid_weekdays(cleaned, clean_module):
    observed_days = set(cleaned["Day"].dropna().unique())
    assert observed_days.issubset(set(clean_module.DAY_ORDER))


# --- Missingness ---------------------------------------------------------------

def test_no_missing_values_in_critical_columns(cleaned):
    """Date, Time (via Hour), and Min Delay are required for the
    estimands, so they must never be missing after cleaning."""
    for column in ["Date", "Hour", "Min Delay", "Positive Delay"]:
        assert not cleaned[column].isna().any(), f"{column} has unexpected missing values"


def test_no_rows_dropped_for_missing_bound_line_station_code(raw, cleaned):
    """Bound, Line, Station, and Code aren't required for either estimand,
    so cleaning should never remove a row on their account."""
    assert len(cleaned) == len(raw)


# --- Derived variables -----------------------------------------------------------

def test_positive_delay_matches_its_definition(cleaned):
    assert (cleaned["Positive Delay"] == (cleaned["Min Delay"] > 0)).all()


def test_positive_delay_minutes_matches_min_delay_when_positive(cleaned):
    positive = cleaned[cleaned["Positive Delay"]]
    assert (positive["Positive Delay Minutes"] == positive["Min Delay"]).all()


def test_positive_delay_minutes_is_missing_when_not_positive(cleaned):
    zero = cleaned[~cleaned["Positive Delay"]]
    assert zero["Positive Delay Minutes"].isna().all()


# --- Analysis outputs -----------------------------------------------------------

def test_hourly_table_has_24_rows(analyzed):
    hourly, _results = analyzed
    assert len(hourly) == 24


def test_hourly_observations_sum_to_total(cleaned, analyzed):
    hourly, _results = analyzed
    assert hourly["observations"].sum() == len(cleaned)


def test_positive_and_zero_counts_add_up(cleaned, analyzed):
    _hourly, results = analyzed
    assert results["n_positive_delays"] + results["n_zero_delays"] == len(cleaned)


def test_positive_delay_percent_in_range(analyzed):
    hourly, results = analyzed
    assert 0 <= results["positive_delay_percent"] <= 100
    assert hourly["positive_delay_percent"].between(0, 100).all()


def test_line_quality_counts_add_up(cleaned, analyzed):
    _hourly, results = analyzed
    total = results["line_n_missing"] + results["line_n_dirty"] + results["line_n_clean"]
    assert total == len(cleaned)

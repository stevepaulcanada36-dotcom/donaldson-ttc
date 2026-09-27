from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_PATH = PROJECT_ROOT / "data/raw_data/TTC_Subway_Delay_Data_2024.xlsx"


def test_2024_reference_has_expected_schema_and_nonempty_data():
    data = pd.read_excel(REFERENCE_PATH)
    expected = {"Date", "Time", "Day", "Station", "Code", "Min Delay", "Min Gap", "Bound", "Line", "Vehicle"}
    assert expected.issubset(data.columns)
    assert len(data) > 0


def test_2024_reference_date_and_delay_validity():
    data = pd.read_excel(REFERENCE_PATH)
    assert pd.to_datetime(data["Date"], errors="coerce").notna().all()
    delay = pd.to_numeric(data["Min Delay"], errors="coerce")
    assert delay.notna().all()
    assert (delay >= 0).all()


def test_2024_hourly_partition_covers_all_rows():
    data = pd.read_excel(REFERENCE_PATH)
    hour = pd.to_datetime(data["Time"].astype(str), format="mixed", errors="coerce").dt.hour
    assert hour.notna().all()
    assert hour.between(0, 23).all()
    assert hour.value_counts().sum() == len(data)


from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_PATH = PROJECT_ROOT / "data/raw_data/TTC_Subway_Delay_Data_since_2025.csv"
ANALYSIS_DATA_PATH = PROJECT_ROOT / "data/analysis_data/ttc_delay_analysis.parquet"
DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def prepare_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean the raw TTC extract into an analysis-ready frame.

    No observation is removed for a missing ``Bound``, ``Line``, ``Station``,
    or ``Code`` value, since none of those variables is required to compute
    the primary or secondary estimand. A missing or negative ``Min Delay``
    would break the estimands directly, so those are checked with
    assertions rather than silently patched: if the assumption stops
    holding (for example, if a future refresh of the TTC file introduces
    missing values), the pipeline fails loudly instead of quietly changing
    the analysis population.

    Adds the derived variables used throughout the analysis:

    - ``Hour``: the hour of day (0-23) parsed from ``Time``.
    - ``Day``: the day of the week, derived from ``Date`` (as an ordered
      category), independent of the raw file's own ``Day`` column.
    - ``Month``: the year-month period, derived from ``Date``.
    - ``Positive Delay``: True when ``Min Delay > 0``.
    - ``Positive Delay Minutes``: ``Min Delay`` where positive, else NA.
    """
    data = df.copy()
    data["Date"] = pd.to_datetime(data["Date"])
    data["Hour"] = pd.to_datetime(data["Time"], format="%H:%M").dt.hour
    data["Day"] = pd.Categorical(data["Date"].dt.day_name(), categories=DAY_ORDER, ordered=True)
    data["Month"] = data["Date"].dt.to_period("M").astype(str)

    assert data["Min Delay"].notna().all(), (
        "Min Delay has missing values; the current pipeline assumes none. "
        "Decide explicitly how to handle them before proceeding."
    )
    assert (data["Min Delay"] >= 0).all(), (
        "Found a negative Min Delay value; this indicates a data issue that "
        "should be investigated, not silently analyzed."
    )
    assert data["Hour"].between(0, 23).all(), "Hour should always be between 0 and 23 after parsing Time."

    data["Positive Delay"] = data["Min Delay"] > 0
    data["Positive Delay Minutes"] = data["Min Delay"].where(data["Positive Delay"])
    return data


def main() -> None:
    raw = pd.read_csv(RAW_DATA_PATH)
    cleaned = prepare_data(raw)

    ANALYSIS_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    cleaned.to_parquet(ANALYSIS_DATA_PATH, index=False)

    print(
        f"Cleaned {len(cleaned):,} observations from {RAW_DATA_PATH} "
        f"and saved the analysis dataset to {ANALYSIS_DATA_PATH}."
    )


if __name__ == "__main__":
    main()

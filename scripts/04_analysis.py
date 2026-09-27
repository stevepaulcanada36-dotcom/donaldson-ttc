import json
from pathlib import Path

import pandas as pd



PROJECT_ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_DATA_PATH = PROJECT_ROOT / "data/analysis_data/ttc_delay_analysis.parquet"
OUTPUT_PATH = PROJECT_ROOT / "outputs"
TABLES_PATH = OUTPUT_PATH / "tables"


# Recognized subway line codes. Used only to flag Line values that are
# clearly not a subway line (e.g. a bus route number or free text), not to
# drop or alter any observation.
SUBWAY_LINE_TOKENS = {"YU", "BD", "SHP", "SRT", "EC", "YUS"}

# A Code needs at least this many observations before its Bound-missingness
# rate is treated as informative for the min/max pattern summary.
MIN_CODE_COUNT_FOR_PATTERN = 200


def wilson_interval(successes: pd.Series, observations: pd.Series) -> tuple[pd.Series, pd.Series]:
    z = 1.96
    rate = successes / observations
    denominator = 1 + z**2 / observations
    centre = (rate + z**2 / (2 * observations)) / denominator
    margin = (
        z
        * ((rate * (1 - rate) / observations) + z**2 / (4 * observations**2)) ** 0.5
        / denominator
    )
    low = (centre - margin).clip(lower=0)
    high = (centre + margin).clip(upper=1)
    return low, high


def is_clean_subway_line(value: object) -> bool | None:
    """True if `value` is a recognized subway line code (or combination),
    False if it is present but not recognized (e.g. a bus/streetcar route
    name or other free text), None if missing."""
    if pd.isna(value):
        return None
    tokens = [token.strip() for token in str(value).replace("/", " ").split()]
    return bool(tokens) and all(token in SUBWAY_LINE_TOKENS for token in tokens)


def summarize_line_quality(data: pd.DataFrame) -> dict[str, object]:
    classification = data["Line"].apply(is_clean_subway_line)
    n_missing = int(classification.isna().sum())
    n_dirty = int((classification == False).sum())  # noqa: E712
    n_clean = int((classification == True).sum())  # noqa: E712
    return {
        "line_n_missing": n_missing,
        "line_n_missing_percent": round(n_missing / len(data) * 100, 2),
        "line_n_dirty": n_dirty,
        "line_n_dirty_percent": round(n_dirty / len(data) * 100, 2),
        "line_n_clean": n_clean,
    }


def summarize_bound_pattern(data: pd.DataFrame) -> dict[str, object]:
    bound_missing = data["Bound"].isna()
    code_counts = data["Code"].value_counts()
    common_codes = code_counts[code_counts >= MIN_CODE_COUNT_FOR_PATTERN].index
    if len(common_codes) == 0:
        return {
            "bound_missing_percent": round(float(bound_missing.mean() * 100), 2),
            "bound_pattern_by_code_min_percent": None,
            "bound_pattern_by_code_max_percent": None,
        }
    rate_by_code = (
        data[data["Code"].isin(common_codes)].groupby("Code")["Bound"].apply(lambda s: s.isna().mean())
    )
    return {
        "bound_missing_percent": round(float(bound_missing.mean() * 100), 2),
        "bound_pattern_by_code_min_percent": round(float(rate_by_code.min() * 100), 2),
        "bound_pattern_by_code_max_percent": round(float(rate_by_code.max() * 100), 2),
    }


def summarize_hourly(data: pd.DataFrame) -> pd.DataFrame:
    summary = (
        data.groupby("Hour")
        .agg(
            observations=("Min Delay", "size"),
            positive_delays=("Positive Delay", "sum"),
            positive_delay_percent=("Positive Delay", "mean"),
            mean_positive_delay=("Positive Delay Minutes", "mean"),
            median_positive_delay=("Positive Delay Minutes", "median"),
            p95_positive_delay=("Positive Delay Minutes", lambda values: values.quantile(0.95)),
        )
        .reset_index()
    )
    summary["positive_delay_percent"] *= 100
    low, high = wilson_interval(summary["positive_delays"], summary["observations"])
    summary["rate_ci_low_percent"] = low * 100
    summary["rate_ci_high_percent"] = high * 100
    return summary


def cramers_v(table: pd.DataFrame) -> float:
    observed = table.to_numpy(dtype=float)
    n = observed.sum()
    row = observed.sum(axis=1, keepdims=True)
    col = observed.sum(axis=0, keepdims=True)
    expected = row @ col / n
    chi2 = ((observed - expected) ** 2 / expected).sum()
    return float((chi2 / n / min(observed.shape[0] - 1, observed.shape[1] - 1)) ** 0.5)


def analyze(data: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    hourly = summarize_hourly(data)
    overall_rate = float(data["Positive Delay"].mean() * 100)
    hourly["rate_difference_pp_vs_overall"] = hourly["positive_delay_percent"] - overall_rate
    hourly["prevalence_ratio_vs_overall"] = hourly["positive_delay_percent"] / overall_rate
    positive = data[data["Positive Delay"]]
    association_table = pd.crosstab(data["Hour"], data["Positive Delay"]).to_numpy(dtype=float)
    n = association_table.sum()
    expected = association_table.sum(axis=1, keepdims=True) @ association_table.sum(axis=0, keepdims=True) / n
    chi_square = float(((association_table - expected) ** 2 / expected).sum())
    results = {
        "n_observations": int(len(data)),
        "date_min": str(data["Date"].min().date()),
        "date_max": str(data["Date"].max().date()),
        "n_positive_delays": int(len(positive)),
        "positive_delay_count": int(len(positive)),
        "n_zero_delays": int((~data["Positive Delay"]).sum()),
        "positive_delay_percent": round(float(data["Positive Delay"].mean() * 100), 2),
        "mean_positive_delay": round(float(positive["Min Delay"].mean()), 2),
        "median_positive_delay": round(float(positive["Min Delay"].median()), 2),
        "p95_positive_delay": round(float(positive["Min Delay"].quantile(0.95)), 2),
        "max_min_delay": int(data["Min Delay"].max()),
        "highest_delay_hour": int(hourly.loc[hourly["positive_delay_percent"].idxmax(), "Hour"]),
        "highest_delay_hour_percent": round(float(hourly["positive_delay_percent"].max()), 2),
        "lowest_delay_hour": int(hourly.loc[hourly["positive_delay_percent"].idxmin(), "Hour"]),
        "lowest_delay_hour_percent": round(float(hourly["positive_delay_percent"].min()), 2),
        "hour_chi_square": round(chi_square, 2),
        "hour_cramers_v": round(cramers_v(pd.crosstab(data["Hour"], data["Positive Delay"])), 4),
        "max_to_min_hour_rate_ratio": round(float(hourly["positive_delay_percent"].max() / hourly["positive_delay_percent"].min()), 2),
    }
    results.update(summarize_line_quality(data))
    results.update(summarize_bound_pattern(data))
    return hourly, results


def main() -> None:
    data = pd.read_parquet(ANALYSIS_DATA_PATH)
    hourly, results = analyze(data)

    weekday = (
        data.groupby("Day", observed=False)
        .agg(
            observations=("Min Delay", "size"),
            positive_delays=("Positive Delay", "sum"),
            positive_delay_percent=("Positive Delay", "mean"),
            median_positive_delay=("Positive Delay Minutes", "median"),
        )
        .reset_index()
    )
    weekday["positive_delay_percent"] *= 100
    weekday_low, weekday_high = wilson_interval(weekday["positive_delays"], weekday["observations"])
    weekday["rate_ci_low_percent"] = weekday_low * 100
    weekday["rate_ci_high_percent"] = weekday_high * 100

    monthly = (
        data.groupby("Month")
        .agg(
            observations=("Min Delay", "size"),
            positive_delays=("Positive Delay", "sum"),
            positive_delay_percent=("Positive Delay", "mean"),
        )
        .reset_index()
    )
    monthly["positive_delay_percent"] *= 100

    station_summary = pd.DataFrame({
        "Measure": [
            "Observations",
            "Distinct station/location strings",
            "Missing Bound (%)",
            "Missing Line (%)",
            "Missing Station (%)",
            "Missing Code (%)",
        ],
        "Value": [
            len(data),
            data["Station"].nunique(dropna=True),
            round(data["Bound"].isna().mean() * 100, 2),
            round(data["Line"].isna().mean() * 100, 2),
            round(data["Station"].isna().mean() * 100, 2),
            round(data["Code"].isna().mean() * 100, 2),
        ],
    })

    positive = data.loc[data["Positive Delay"], "Min Delay"]
    data_profile = pd.DataFrame({
        "Measure": [
            "Observations",
            "Date range",
            "Positive-delay observations",
            "Positive-delay rate (%)",
            "Median positive delay (min)",
            "Mean positive delay (min)",
            "95th percentile positive delay (min)",
            "Maximum recorded delay (min)",
        ],
        "Value": [
            f"{len(data):,}",
            f"{data['Date'].min().date()} to {data['Date'].max().date()}",
            f"{len(positive):,}",
            round(float(data["Positive Delay"].mean() * 100), 2),
            round(float(positive.median()), 2),
            round(float(positive.mean()), 2),
            round(float(positive.quantile(0.95)), 2),
            int(data["Min Delay"].max()),
        ],
    })

    assert hourly["observations"].sum() == len(data)
    assert results["n_positive_delays"] + results["n_zero_delays"] == len(data)

    TABLES_PATH.mkdir(parents=True, exist_ok=True)
    hourly.to_csv(TABLES_PATH / "hourly_summary.csv", index=False)
    weekday.to_csv(TABLES_PATH / "weekday_summary.csv", index=False)
    monthly.to_csv(TABLES_PATH / "monthly_summary.csv", index=False)
    station_summary.to_csv(TABLES_PATH / "data_quality_summary.csv", index=False)
    data_profile.to_csv(TABLES_PATH / "data_profile.csv", index=False)
    (OUTPUT_PATH / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()

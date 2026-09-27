import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_PATH = PROJECT_ROOT / "data/raw_data/TTC_Subway_Delay_Data_2024.xlsx"
ANALYSIS_PATH = PROJECT_ROOT / "data/analysis_data/ttc_delay_analysis.parquet"
TABLES_PATH = PROJECT_ROOT / "outputs/tables"


def wilson(successes: pd.Series, n: pd.Series):
    z = 1.96
    p = successes / n
    den = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / den
    margin = z * ((p * (1 - p) / n) + z**2 / (4 * n**2)) ** 0.5 / den
    low = (centre - margin).clip(lower=0)
    high = (centre + margin).clip(upper=1)
    return low, high


def cramers_v(table: pd.DataFrame) -> float:
    observed = table.to_numpy(dtype=float)
    n = observed.sum()
    row = observed.sum(axis=1, keepdims=True)
    col = observed.sum(axis=0, keepdims=True)
    expected = row @ col / n
    chi2 = ((observed - expected) ** 2 / expected).sum()
    phi2 = chi2 / n
    r, k = observed.shape
    return float((phi2 / min(k - 1, r - 1)) ** 0.5)


def prepare_2024() -> pd.DataFrame:
    raw = pd.read_excel(REFERENCE_PATH)
    required = {"Date", "Time", "Code", "Min Delay"}
    missing = required - set(raw.columns)
    if missing:
        raise ValueError(f"2024 file is missing columns: {sorted(missing)}")
    raw["Date"] = pd.to_datetime(raw["Date"], errors="coerce")
    raw["Time"] = raw["Time"].astype(str).str.strip()
    parsed = pd.to_datetime(raw["Time"], format="%H:%M", errors="coerce")
    if parsed.isna().any():
        parsed = pd.to_datetime(raw["Time"], errors="coerce")
    raw["Hour"] = parsed.dt.hour
    raw["Min Delay"] = pd.to_numeric(raw["Min Delay"], errors="coerce")
    raw = raw.dropna(subset=["Date", "Hour", "Min Delay"]).copy()
    raw["Positive Delay"] = raw["Min Delay"] > 0
    raw["Positive Delay Minutes"] = raw["Min Delay"].where(raw["Positive Delay"])
    return raw


def hourly(data: pd.DataFrame) -> pd.DataFrame:
    out = data.groupby("Hour").agg(
        observations=("Min Delay", "size"),
        positive_delays=("Positive Delay", "sum"),
        positive_delay_rate=("Positive Delay", "mean"),
        median_positive_delay=("Positive Delay Minutes", "median"),
    ).reset_index()
    out["positive_delay_rate"] *= 100
    lo, hi = wilson(out["positive_delays"], out["observations"])
    out["rate_ci_low"] = lo * 100
    out["rate_ci_high"] = hi * 100
    return out


def add_effects(h: pd.DataFrame, overall_rate: float) -> pd.DataFrame:
    h = h.copy()
    h["rate_difference_pp"] = h["positive_delay_rate"] - overall_rate
    h["prevalence_ratio_vs_overall"] = h["positive_delay_rate"] / overall_rate
    return h



def main():
    TABLES_PATH.mkdir(parents=True, exist_ok=True)
    if not REFERENCE_PATH.exists():
        raise FileNotFoundError(f"Missing downloaded 2024 reference file: {REFERENCE_PATH}. Run scripts/02_download_data.py first.")
    data24 = prepare_2024()
    h24 = hourly(data24)
    overall24 = data24["Positive Delay"].mean() * 100
    h24 = add_effects(h24, overall24)
    h24.to_csv(TABLES_PATH / "hourly_2024_summary.csv", index=False)

    # A formal association summary is reported as a descriptive effect-size calculation.
    table24 = pd.crosstab(data24["Hour"], data24["Positive Delay"])
    v24 = cramers_v(table24)
    summary24 = {
        "n_observations": int(len(data24)),
        "date_min": str(data24["Date"].min().date()),
        "date_max": str(data24["Date"].max().date()),
        "positive_delay_percent": round(float(overall24), 2),
        "median_positive_delay": round(float(data24.loc[data24["Positive Delay"], "Min Delay"].median()), 2),
        "highest_delay_hour": int(h24.loc[h24["positive_delay_rate"].idxmax(), "Hour"]),
        "highest_delay_hour_percent": round(float(h24["positive_delay_rate"].max()), 2),
        "lowest_delay_hour": int(h24.loc[h24["positive_delay_rate"].idxmin(), "Hour"]),
        "lowest_delay_hour_percent": round(float(h24["positive_delay_rate"].min()), 2),
        "hour_cramers_v": round(v24, 4),
        "bound_missing_percent": round(float(data24["Bound"].isna().mean() * 100), 2) if "Bound" in data24 else None,
        "line_missing_percent": round(float(data24["Line"].isna().mean() * 100), 2) if "Line" in data24 else None,
    }
    (PROJECT_ROOT / "outputs/summary_2024.json").write_text(json.dumps(summary24, indent=2) + "\n")

    if ANALYSIS_PATH.exists():
        current = pd.read_parquet(ANALYSIS_PATH)
        hc = hourly(current)
        overall_current = current["Positive Delay"].mean() * 100
        hc = add_effects(hc, overall_current)
        compare = hc[["Hour", "positive_delay_rate", "median_positive_delay"]].rename(columns={
            "positive_delay_rate": "rate_since_2025",
            "median_positive_delay": "median_since_2025",
        }).merge(
            h24[["Hour", "positive_delay_rate", "median_positive_delay"]].rename(columns={
                "positive_delay_rate": "rate_2024",
                "median_positive_delay": "median_2024",
            }), on="Hour", how="outer"
        ).sort_values("Hour")
        compare["rate_difference_pp_since_2025_minus_2024"] = compare["rate_since_2025"] - compare["rate_2024"]
        compare["median_difference_minutes_since_2025_minus_2024"] = compare["median_since_2025"] - compare["median_2024"]
        compare.to_csv(TABLES_PATH / "hourly_2024_vs_since_2025.csv", index=False)

        combined = pd.concat([
            current[["Hour", "Positive Delay", "Min Delay"]].assign(period="Since 2025"),
            data24[["Hour", "Positive Delay", "Min Delay"]].assign(period="2024"),
        ], ignore_index=True)
        table = pd.crosstab(combined["Hour"].astype(str) + "|" + combined["period"], combined["Positive Delay"])
        combined_v = cramers_v(pd.crosstab(combined["Hour"], combined["Positive Delay"]))
        (PROJECT_ROOT / "outputs/comparison_effects.json").write_text(json.dumps({
            "hour_cramers_v_2024": v24,
            "hour_cramers_v_combined": combined_v,
            "overall_positive_rate_2024": overall24,
            "overall_positive_rate_since_2025": float(overall_current),
        }, indent=2) + "\n")

    print(json.dumps(summary24, indent=2))


if __name__ == "__main__":
    main()

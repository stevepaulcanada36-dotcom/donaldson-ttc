from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_PATH = PROJECT_ROOT / "data/raw_data/TTC_Subway_Delay_Data_2024.xlsx"
OUTPUT_PATH = PROJECT_ROOT / "outputs/ttc_quality_check.xlsx"


def main():
    if not REFERENCE_PATH.exists():
        raise FileNotFoundError(f"Missing downloaded 2024 reference file: {REFERENCE_PATH}. Run scripts/02_download_data.py first.")
    raw = pd.read_excel(REFERENCE_PATH, sheet_name=0)
    checks = []
    checks.append(("Row count > 0", len(raw) > 0, len(raw)))
    checks.append(("Required columns present", set(["Date", "Time", "Min Delay", "Code"]).issubset(raw.columns), ""))
    checks.append(("Date values parse", pd.to_datetime(raw["Date"], errors="coerce").notna().all(), int(pd.to_datetime(raw["Date"], errors="coerce").isna().sum())))
    checks.append(("Min Delay numeric", pd.to_numeric(raw["Min Delay"], errors="coerce").notna().all(), int(pd.to_numeric(raw["Min Delay"], errors="coerce").isna().sum())))
    checks.append(("Min Delay non-negative", (pd.to_numeric(raw["Min Delay"], errors="coerce") >= 0).all(), int((pd.to_numeric(raw["Min Delay"], errors="coerce") < 0).sum())))
    checks.append(("Time values parse", pd.to_datetime(raw["Time"].astype(str), format="mixed", errors="coerce").notna().all(), int(pd.to_datetime(raw["Time"].astype(str), format="mixed", errors="coerce").isna().sum())))

    hourly = raw.assign(
        Hour=pd.to_datetime(raw["Time"].astype(str), format="mixed", errors="coerce").dt.hour,
        Positive_Delay=pd.to_numeric(raw["Min Delay"], errors="coerce") > 0,
    ).groupby("Hour").agg(
        observations=("Min Delay", "size"),
        positive_delays=("Positive_Delay", "sum"),
        positive_delay_rate=("Positive_Delay", "mean"),
    ).reset_index()
    hourly["positive_delay_rate"] *= 100

    monthly = raw.assign(
        Month=pd.to_datetime(raw["Date"], errors="coerce").dt.to_period("M").astype(str),
        Positive_Delay=pd.to_numeric(raw["Min Delay"], errors="coerce") > 0,
    ).groupby("Month").agg(
        observations=("Min Delay", "size"),
        positive_delays=("Positive_Delay", "sum"),
        positive_delay_rate=("Positive_Delay", "mean"),
    ).reset_index()
    monthly["positive_delay_rate"] *= 100

    quality = raw.isna().mean().mul(100).round(2).rename("missing_percent").reset_index().rename(columns={"index":"column"})
    summary = pd.DataFrame(checks, columns=["check", "passed", "detail"])

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(OUTPUT_PATH, engine="openpyxl") as writer:
        summary.to_excel(writer, sheet_name="Checks", index=False)
        quality.to_excel(writer, sheet_name="Missingness", index=False)
        hourly.to_excel(writer, sheet_name="Hourly_2024", index=False)
        monthly.to_excel(writer, sheet_name="Monthly_2024", index=False)
        raw.describe(include="all").transpose().to_excel(writer, sheet_name="Describe")
        for ws in writer.book.worksheets:
            for cell in ws[1]:
                cell.font = Font(bold=True)
    if not summary["passed"].all():
        raise AssertionError(summary.loc[~summary["passed"]].to_string(index=False))
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TABLES_PATH = PROJECT_ROOT / "outputs/tables"
ANALYSIS_DATA_PATH = PROJECT_ROOT / "data/analysis_data/ttc_delay_analysis.parquet"
FIGURES_PATH = PROJECT_ROOT / "outputs/figures"

# Keep the paper figures visually restrained. The reference papers use a
# mostly monochrome academic style, so the figures avoid the default bright
# matplotlib colour cycle and let the captions carry the interpretation.
INK = "#333333"
MID_GRAY = "#777777"
LIGHT_GRAY = "#D9D9D9"
POINT_GRAY = "#8A8A8A"


def save_figure(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.close()


def main() -> None:
    hourly = pd.read_csv(TABLES_PATH / "hourly_summary.csv")
    monthly = pd.read_csv(TABLES_PATH / "monthly_summary.csv")
    data = pd.read_parquet(ANALYSIS_DATA_PATH)
    FIGURES_PATH.mkdir(parents=True, exist_ok=True)

    # Figure 1: every original observation is represented by a delay bin.
    # The bin counts sum to the full dataset, including the zero-delay mass.
    bins = [-0.5, 0.5, 5.5, 15.5, 30.5, 60.5, 120.5, 300.5, 600.5, 900.5, np.inf]
    labels = ["0", "1–5", "6–15", "16–30", "31–60", "61–120",
              "121–300", "301–600", "601–900", "901+"]
    distribution = (
        pd.cut(data["Min Delay"], bins=bins, labels=labels)
        .value_counts()
        .reindex(labels, fill_value=0)
    )
    plt.figure(figsize=(9, 5))
    plt.bar(distribution.index.astype(str), distribution.values, color=MID_GRAY)
    plt.xlabel("Recorded delay (minutes)")
    plt.ylabel("Number of recorded observations")
    plt.grid(axis="y", alpha=0.25, color=LIGHT_GRAY)
    save_figure(FIGURES_PATH / "delay_distribution.png")

    # Figure 2: hourly positive-delay prevalence with a descriptive Wilson
    # interval around the observed proportion.
    plt.figure(figsize=(9, 5))
    plt.plot(hourly["Hour"], hourly["positive_delay_percent"], marker="o",
             linewidth=1.8, markersize=4, color=INK)
    plt.fill_between(
        hourly["Hour"],
        hourly["rate_ci_low_percent"],
        hourly["rate_ci_high_percent"],
        color=LIGHT_GRAY,
        alpha=0.8,
        label="95% Wilson interval",
    )
    plt.xlabel("Hour of day")
    plt.ylabel("Recorded observations with positive delay (%)")
    plt.xticks(range(24))
    plt.grid(axis="y", alpha=0.25, color=LIGHT_GRAY)
    plt.legend(frameon=False)
    save_figure(FIGURES_PATH / "positive_delay_rate_by_hour.png")

    # Figure 3: hourly median among positive-delay observations.
    plt.figure(figsize=(9, 5))
    plt.plot(hourly["Hour"], hourly["median_positive_delay"], marker="o",
             linewidth=1.8, markersize=4, color=INK)
    plt.xlabel("Hour of day")
    plt.ylabel("Median recorded delay among positive records (minutes)")
    plt.xticks(range(24))
    plt.grid(axis="y", alpha=0.25, color=LIGHT_GRAY)
    save_figure(FIGURES_PATH / "median_positive_delay_by_hour.png")

    # Figure 4: show every positive-delay observation. There is no boxplot:
    # the rubric discourages boxplots, while this plot retains the actual data.
    rng = np.random.default_rng(2026)
    positive = data.loc[data["Positive Delay"], ["Hour", "Min Delay"]].copy()

    plt.figure(figsize=(11, 5.5))
    for hour in range(24):
        values = positive.loc[positive["Hour"] == hour, "Min Delay"].to_numpy()
        jitter = rng.uniform(-0.18, 0.18, size=len(values))
        plt.scatter(
            hour + jitter,
            values,
            s=5,
            alpha=0.14,
            color=POINT_GRAY,
            linewidths=0,
        )
    plt.plot(
        range(24),
        hourly["median_positive_delay"],
        marker="o",
        linewidth=2,
        markersize=3,
        color=INK,
        label="Hourly median",
    )
    plt.yscale("symlog", linthresh=1)
    plt.xlabel("Hour of day")
    plt.ylabel("Recorded positive delay (minutes; symmetric log scale)")
    plt.xticks(range(24))
    plt.grid(axis="y", alpha=0.25, color=LIGHT_GRAY)
    plt.legend(frameon=False)
    save_figure(FIGURES_PATH / "positive_delay_observations_by_hour.png")

    # Figure 5: supporting monthly pattern.
    plt.figure(figsize=(10, 5))
    plt.plot(monthly["Month"], monthly["positive_delay_percent"], marker="o",
             linewidth=1.8, markersize=4, color=INK)
    plt.xlabel("Month")
    plt.ylabel("Recorded observations with positive delay (%)")
    plt.xticks(rotation=60, ha="right")
    plt.grid(axis="y", alpha=0.25, color=LIGHT_GRAY)
    save_figure(FIGURES_PATH / "positive_delay_rate_by_month.png")

    # Figure 6: historical benchmark against 2024.
    comparison_path = TABLES_PATH / "hourly_2024_vs_since_2025.csv"
    if comparison_path.exists():
        comparison = pd.read_csv(comparison_path)
        plt.figure(figsize=(10, 5))
        plt.plot(comparison["Hour"], comparison["rate_2024"], marker="o",
                 linewidth=1.7, markersize=4, color=MID_GRAY, label="2024")
        plt.plot(comparison["Hour"], comparison["rate_since_2025"], marker="o",
                 linewidth=1.9, markersize=4, color=INK, label="Since 2025")
        plt.xlabel("Hour of day")
        plt.ylabel("Recorded observations with positive delay (%)")
        plt.xticks(range(24))
        plt.grid(axis="y", alpha=0.25, color=LIGHT_GRAY)
        plt.legend(frameon=False)
        save_figure(FIGURES_PATH / "hourly_2024_vs_since_2025.png")

    print(f"Saved figures to {FIGURES_PATH}.")


if __name__ == "__main__":
    main()

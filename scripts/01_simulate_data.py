"""Simulate a small TTC-like dataset for testing the analysis pipeline.

The simulation is deliberately synthetic. It combines hour-of-day and incident
code effects on the probability of a positive delay, and makes delay size and
gap depend on whether a positive delay occurred. The values are not estimates
from the real TTC data; they exist to exercise the project's transformations
and statistical checks before the actual source file is downloaded.
"""

from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = PROJECT_ROOT / "outputs/simulated_data.csv"
N_OBSERVATIONS = 2000

# Hour -> baseline probability of a positive delay.
HOURLY_POSITIVE_RATE = {
    0: 0.10, 1: 0.08, 2: 0.06, 3: 0.05, 4: 0.07, 5: 0.20,
    6: 0.45, 7: 0.40, 8: 0.35, 9: 0.25, 10: 0.20, 11: 0.20,
    12: 0.22, 13: 0.22, 14: 0.22, 15: 0.25, 16: 0.30, 17: 0.32,
    18: 0.28, 19: 0.22, 20: 0.18, 21: 0.15, 22: 0.14, 23: 0.12,
}

# Incident-code effects make the simulated positive-delay probability depend
# on both hour and incident type rather than on hour alone.
CODE_RATE_MULTIPLIER = {
    "ME": 1.15,
    "SU": 1.10,
    "PR": 1.00,
    "MUP": 0.90,
    "SHP": 0.80,
}

DELAY_SIZES = np.array([3, 5, 10, 20, 45])
DELAY_SIZE_PROBS = np.array([0.40, 0.30, 0.18, 0.09, 0.03])
CODE_OPTIONS = list(CODE_RATE_MULTIPLIER)
STATION_TO_LINE = {
    "FINCH": "YU",
    "BLOOR": "BD",
    "KENNEDY": "SRT",
    "SPADINA": "YU/BD",
    "UNION": "YU",
    "KIPLING": "BD",
    "SHEPPARD": "YU",
    "YORKDALE": "YU",
}


def simulate(rng: np.random.Generator, n: int) -> pd.DataFrame:
    dates = pd.Timestamp("2025-01-01") + pd.to_timedelta(
        rng.integers(0, 365, size=n), unit="D"
    )
    hours = rng.integers(0, 24, size=n)
    minutes = rng.integers(0, 60, size=n)
    codes = rng.choice(CODE_OPTIONS, size=n, p=[0.25, 0.20, 0.25, 0.20, 0.10])
    stations = rng.choice(list(STATION_TO_LINE), size=n)
    lines = pd.Series(stations).map(STATION_TO_LINE).to_numpy()

    base_rate = np.array([HOURLY_POSITIVE_RATE[h] for h in hours])
    code_multiplier = np.array([CODE_RATE_MULTIPLIER[c] for c in codes])
    positive_rate = np.clip(base_rate * code_multiplier, 0, 0.95)
    is_positive = rng.random(n) < positive_rate

    min_delay = np.where(
        is_positive,
        rng.choice(DELAY_SIZES, size=n, p=DELAY_SIZE_PROBS),
        0,
    )
    min_gap = np.where(
        is_positive,
        min_delay + rng.integers(0, 6, size=n),
        rng.integers(0, 3, size=n),
    )

    bound = rng.choice(["N", "S", "E", "W"], size=n, p=[0.28, 0.28, 0.22, 0.22])
    vehicles = rng.integers(1000, 9999, size=n)

    return pd.DataFrame({
        "Date": dates.strftime("%Y-%m-%d"),
        "Time": [f"{h:02d}:{m:02d}" for h, m in zip(hours, minutes)],
        "Day": dates.day_name(),
        "Station": stations,
        "Code": codes,
        "Min Delay": min_delay,
        "Min Gap": min_gap,
        "Bound": bound,
        "Line": lines,
        "Vehicle": vehicles,
        "Hour": hours,
    })


def main() -> None:
    rng = np.random.default_rng(2026)
    simulated = simulate(rng, N_OBSERVATIONS)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    simulated.to_csv(OUTPUT_PATH, index=False)
    print(f"Created {len(simulated):,} simulated observations at {OUTPUT_PATH}.")


if __name__ == "__main__":
    main()

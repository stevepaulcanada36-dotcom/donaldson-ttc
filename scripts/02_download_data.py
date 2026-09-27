"""Download the official TTC subway-delay resources from Toronto Open Data.

This script discovers resource URLs from the City's CKAN metadata API rather than
embedding a hand-copied file in the repository. It downloads both the current
since-2025 resource and the official 2024 annual benchmark.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_ID = "996cfe8d-fb35-40ce-b569-698d51fc683b"
CKAN_API_URL = (
    "https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/package_show"
    f"?id={DATASET_ID}"
)
DATASET_PAGE = (
    "https://open.toronto.ca/dataset/996cfe8d-fb35-40ce-b569-698d51fc683b/"
)
RAW_DIR = PROJECT_ROOT / "data" / "raw_data"
PROVENANCE_PATH = PROJECT_ROOT / "outputs" / "data_download.json"

CURRENT_RESOURCE_NAME = "TTC Subway Delay Data since 2025"
CURRENT_FILENAME = "TTC_Subway_Delay_Data_since_2025.csv"
HISTORICAL_RESOURCE_NAME = "ttc-subway-delay-data-2024"
HISTORICAL_FILENAME = "TTC_Subway_Delay_Data_2024.xlsx"

HEADERS = {"User-Agent": "donaldson-ttc-reproducible-analysis/0.2"}


def get_resources() -> list[dict]:
    response = requests.get(CKAN_API_URL, timeout=60, headers=HEADERS)
    response.raise_for_status()
    payload = response.json()
    if not payload.get("success"):
        raise RuntimeError("Toronto Open Data CKAN API returned success=false.")
    return payload["result"]["resources"]


def find_resource(resources: list[dict], target_name: str) -> dict:
    target = target_name.casefold()
    exact = [r for r in resources if str(r.get("name", "")).casefold() == target]
    if exact:
        return exact[0]

    contains = [
        r for r in resources
        if target in str(r.get("name", "")).casefold()
        or target in Path(str(r.get("url", ""))).name.casefold()
    ]
    if contains:
        return contains[0]

    available = [str(r.get("name", "")) for r in resources]
    raise RuntimeError(
        f"Could not find TTC resource {target_name!r}. "
        f"Resources reported by the official API: {available}"
    )


def download_resource(resource: dict, output_path: Path) -> dict:
    url = resource.get("url")
    if not url:
        raise RuntimeError(f"Official resource has no download URL: {resource}")

    response = requests.get(url, timeout=120, headers=HEADERS)
    response.raise_for_status()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(response.content)

    return {
        "resource_id": resource.get("id"),
        "resource_name": resource.get("name"),
        "format": resource.get("format"),
        "download_url": url,
        "saved_to": str(output_path.relative_to(PROJECT_ROOT)),
        "file_size_bytes": len(response.content),
        "sha256": hashlib.sha256(response.content).hexdigest(),
    }


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROVENANCE_PATH.parent.mkdir(parents=True, exist_ok=True)

    resources = get_resources()

    current = find_resource(resources, CURRENT_RESOURCE_NAME)
    historical = find_resource(resources, HISTORICAL_RESOURCE_NAME)

    records = [
        download_resource(current, RAW_DIR / CURRENT_FILENAME),
        download_resource(historical, RAW_DIR / HISTORICAL_FILENAME),
    ]

    provenance = {
        "source_dataset": "TTC Subway Delay Data",
        "dataset_page": DATASET_PAGE,
        "ckan_dataset_id": DATASET_ID,
        "download_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "resources": records,
    }
    PROVENANCE_PATH.write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
    )

    for record in records:
        print(
            f"Downloaded {record['resource_name']} to "
            f"{record['saved_to']} ({record['file_size_bytes']:,} bytes)."
        )
    print(f"Wrote download provenance to {PROVENANCE_PATH}.")


if __name__ == "__main__":
    main()

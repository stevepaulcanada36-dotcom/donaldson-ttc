from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "02_download_data.py"
spec = spec_from_file_location("download_data", SCRIPT)
download_data = module_from_spec(spec)
spec.loader.exec_module(download_data)


def test_find_resource_matches_official_resource_name():
    resources = [
        {"id": "a", "name": "TTC Subway Delay Data since 2025", "url": "https://example/current.csv"},
        {"id": "b", "name": "ttc-subway-delay-data-2024", "url": "https://example/2024.xlsx"},
    ]
    found = download_data.find_resource(resources, "ttc-subway-delay-data-2024")
    assert found["id"] == "b"


def test_find_resource_can_match_resource_filename():
    resources = [
        {"id": "a", "name": "Historical TTC data", "url": "https://example/ttc-subway-delay-data-2024.xlsx"},
    ]
    found = download_data.find_resource(resources, "ttc-subway-delay-data-2024")
    assert found["id"] == "a"

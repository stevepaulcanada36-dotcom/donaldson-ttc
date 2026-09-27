import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run_command(command: list[str]) -> None:
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


def run_script(name: str) -> None:
    run_command([sys.executable, str(PROJECT_ROOT / "scripts" / name)])


def run_pytest(*targets: str) -> None:
    run_command([sys.executable, "-m", "pytest", *targets, "-v"])


def main() -> None:
    if shutil.which("quarto") is None:
        raise SystemExit(
            "Quarto is required for the final step but was not found on PATH. "
            "Install Quarto, then rerun this workflow."
        )

    print("\n>>> Running 01_simulate_data.py")
    run_script("01_simulate_data.py")

    print("\n>>> Running simulated-data tests")
    run_pytest("tests/test_simulated.py")

    print("\n>>> Running statistical-helper tests")
    run_pytest("tests/test_analysis.py")

    print("\n>>> Running 02_download_data.py")
    run_script("02_download_data.py")

    print("\n>>> Running 03_clean_data.py")
    run_script("03_clean_data.py")

    print("\n>>> Running actual-data tests")
    run_pytest("tests/test_actual.py")

    print("\n>>> Running 2024 reference-data tests")
    run_pytest("tests/test_reference_2024.py")

    print("\n>>> Running 04_analysis.py")
    run_script("04_analysis.py")

    print("\n>>> Running 06_historical_comparison.py")
    run_script("06_historical_comparison.py")

    print("\n>>> Running 07_excel_quality_check.py")
    run_script("07_excel_quality_check.py")

    print("\n>>> Running 05_visualizations.py")
    run_script("05_visualizations.py")

    print("\n>>> Rendering paper/paper.qmd")
    render_environment = os.environ.copy()
    venv_bin_dir = "Scripts" if os.name == "nt" else "bin"
    venv_path = PROJECT_ROOT / ".venv" / venv_bin_dir
    render_environment["PATH"] = str(venv_path) + os.pathsep + render_environment.get("PATH", "")
    subprocess.run(
        ["quarto", "render", "paper/paper.qmd", "--to", "pdf"],
        cwd=PROJECT_ROOT,
        check=True,
        env=render_environment,
    )

    rendered_pdf = PROJECT_ROOT / "paper" / "paper.pdf"
    assert rendered_pdf.exists(), f"Expected {rendered_pdf} after rendering."
    print(f"\nWorkflow completed successfully: {rendered_pdf}")


if __name__ == "__main__":
    main()

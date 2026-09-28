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


def check_r_packages() -> None:
    """Check that the R packages needed by the final presentation layer are installed."""
    rscript = shutil.which("Rscript")
    if rscript is None:
        raise RuntimeError(
            "Rscript was not found on PATH. Install R and make sure Rscript is available."
        )

    required = ["arrow", "ggplot2", "tinytable"]
    check_code = (
        "pkgs <- c("
        + ", ".join(repr(p) for p in required)
        + "); missing <- pkgs[!vapply(pkgs, requireNamespace, logical(1), quietly=TRUE)]; "
        + "if (length(missing)) { cat(paste(missing, collapse='\\n')); quit(status=10) }"
    )

    result = subprocess.run(
        [rscript, "-e", check_code],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )

    if result.returncode == 10:
        missing = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        packages = ", ".join(missing)
        raise RuntimeError(
            "R is installed, but these required R packages are missing: "
            f"{packages}.\\n\\n"
            "Install them once in R/RStudio with:\\n"
            'install.packages(c("arrow", "ggplot2", "tinytable"))\\n\\n'
            "Then run:\\n"
            "uv run python scripts/run_all.py"
        )

    if result.returncode != 0:
        details = (result.stderr or result.stdout).strip()
        raise RuntimeError(
            "Could not check the installed R packages."
            + (f"\\n\\nR reported:\\n{details}" if details else "")
        )


def run_r_script(name: str) -> None:
    rscript = shutil.which("Rscript")
    if rscript is None:
        raise SystemExit(
            "Rscript is required for the presentation layer but was not found on PATH. "
            "Install R and the required packages, then rerun this workflow."
        )
    run_command([rscript, str(PROJECT_ROOT / "scripts" / name)])


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

    # Python versions of the presentation scripts are retained for reference.
    # They are intentionally not run here because the final paper figures and
    # tables are generated with ggplot2 and tinytable, respectively.
    # print("\n>>> Running Python reference figures")
    # run_script("05_visualizations.py")
    # print("\n>>> Running Python reference tables")
    # run_script("09_make_tables.py")

    print("\n>>> Checking required R packages")
    check_r_packages()

    print("\n>>> Running final R presentation figures with ggplot2")
    run_r_script("08_make_figures.R")

    print("\n>>> Running final R presentation tables with tinytable")
    run_r_script("09_make_tables.R")

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

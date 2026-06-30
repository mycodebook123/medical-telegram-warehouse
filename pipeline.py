"""
Dagster pipeline orchestrating the full medical-telegram-warehouse flow:
scrape -> load raw -> dbt transform -> YOLO enrichment -> load YOLO results.
"""

import subprocess
import sys
from pathlib import Path

from dagster import job, op, ScheduleDefinition, Definitions, OpExecutionContext

PROJECT_ROOT = Path(__file__).parent
DBT_PROJECT_DIR = PROJECT_ROOT / "medical_warehouse"


def run_command(context: OpExecutionContext, cmd: list[str], cwd: Path = PROJECT_ROOT):
    context.log.info(f"Running: {' '.join(cmd)} (cwd={cwd})")
    result = subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True
    )
    context.log.info(result.stdout)
    if result.returncode != 0:
        context.log.error(result.stderr)
        raise Exception(f"Command failed: {' '.join(cmd)}\n{result.stderr}")
    return result.stdout


@op
def scrape_telegram_data(context: OpExecutionContext):
    """Run the Telegram scraper to populate the raw data lake."""
    run_command(context, [sys.executable, "src/scraper.py"])
    return "scrape_complete"


@op
def load_raw_to_postgres(context: OpExecutionContext, _scrape_done):
    """Load raw JSON files from the data lake into PostgreSQL."""
    run_command(context, [sys.executable, "src/load_to_postgres.py"])
    return "load_complete"


@op
def run_dbt_transformations(context: OpExecutionContext, _load_done):
    """Run dbt to build staging and mart models, then test them."""
    run_command(context, ["dbt", "run"], cwd=DBT_PROJECT_DIR)
    run_command(context, ["dbt", "test"], cwd=DBT_PROJECT_DIR)
    return "dbt_complete"


@op
def run_yolo_enrichment(context: OpExecutionContext, _dbt_done):
    """Run YOLO object detection on downloaded images and load results."""
    run_command(context, [sys.executable, "src/yolo_detect.py"])
    run_command(context, [sys.executable, "src/load_yolo_to_postgres.py"])
    run_command(context, ["dbt", "run", "--select", "fct_image_detections"], cwd=DBT_PROJECT_DIR)
    return "yolo_complete"


@job
def medical_warehouse_pipeline():
    """Full ELT pipeline: scrape -> load -> transform -> enrich."""
    scraped = scrape_telegram_data()
    loaded = load_raw_to_postgres(scraped)
    transformed = run_dbt_transformations(loaded)
    run_yolo_enrichment(transformed)


# Daily schedule at 6:00 AM
daily_schedule = ScheduleDefinition(
    job=medical_warehouse_pipeline,
    cron_schedule="0 6 * * *",
    name="daily_medical_warehouse_run",
)

defs = Definitions(
    jobs=[medical_warehouse_pipeline],
    schedules=[daily_schedule],
)
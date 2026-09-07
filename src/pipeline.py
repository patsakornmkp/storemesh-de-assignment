"""
Prefect ETL pipeline: shopdata.db -> analytics.db

Extract   : อ่านข้อมูลดิบจาก 3 views
Transform : ทำความสะอาดลูกค้าและ orders + แปลงสกุลเงินเป็น USD
Load      : เขียนลง analytics.db (dim_customers, fct_orders)
"""

import sqlite3
from pathlib import Path

import pandas as pd
from prefect import flow, get_run_logger, task

from src.transforms import clean_customers, convert_to_usd, filter_invalid_orders

SOURCE_DB = Path("data/shopdata.db")
TARGET_DB = Path("analytics.db")


@task(retries=2, retry_delay_seconds=3)
def extract_view(view_name: str, db_path: Path = SOURCE_DB) -> pd.DataFrame:
    """อ่านข้อมูลทั้งหมดจาก view ที่ระบุ"""
    logger = get_run_logger()
    if not db_path.exists():
        raise FileNotFoundError(f"Source database not found: {db_path}")

    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql_query(f"SELECT * FROM {view_name}", conn)

    logger.info("EXTRACT | %s -> %d rows", view_name, len(df))
    return df


@task
def transform_customers(raw: pd.DataFrame) -> pd.DataFrame:
    """ทำความสะอาดข้อมูลลูกค้าและรายงานจำนวนแถวที่เปลี่ยนไป"""
    logger = get_run_logger()

    missing_email = int(raw["email"].isna().sum())
    cleaned = clean_customers(raw)

    logger.info(
        "TRANSFORM | customers %d -> %d (removed %d duplicates, filled %d missing emails)",
        len(raw), len(cleaned), len(raw) - len(cleaned), missing_email,
    )
    return cleaned


@task
def transform_orders(raw: pd.DataFrame, rates: pd.DataFrame) -> pd.DataFrame:
    """กรอง order ที่ไม่ถูกต้องและแปลงยอดเงินเป็น USD"""
    logger = get_run_logger()

    valid = filter_invalid_orders(raw)
    logger.info(
        "TRANSFORM | orders %d -> %d (dropped %d rows with total_amount <= 0)",
        len(raw), len(valid), len(raw) - len(valid),
    )

    enriched = convert_to_usd(valid, rates)
    unmatched = int((~enriched["fx_rate_matched"]).sum())
    logger.warning(
        "TRANSFORM | FX conversion done | %d rows had no matching rate and used fallback 1.0",
        unmatched,
    )
    return enriched


@task
def load_table(df: pd.DataFrame, table_name: str, db_path: Path = TARGET_DB) -> int:
    """เขียน DataFrame ลงตารางปลายทาง (replace เพื่อให้ pipeline idempotent)"""
    logger = get_run_logger()

    with sqlite3.connect(db_path) as conn:
        df.to_sql(table_name, conn, if_exists="replace", index=False)

    logger.info("LOAD | %s <- %d rows", table_name, len(df))
    return len(df)


@flow(name="shop-etl-pipeline")
def shop_etl_pipeline() -> None:
    """Orchestration หลักของ ETL pipeline"""
    logger = get_run_logger()
    logger.info("=== Starting shop ETL pipeline ===")

    raw_customers = extract_view("vw_raw_customers")
    raw_orders    = extract_view("vw_raw_orders")
    fx_rates      = extract_view("vw_exchange_rates")

    dim_customers = transform_customers(raw_customers)
    fct_orders    = transform_orders(raw_orders, fx_rates)

    n_customers = load_table(dim_customers, "dim_customers")
    n_orders    = load_table(fct_orders, "fct_orders")

    logger.info(
        "=== Pipeline finished | %d customers, %d orders written to %s ===",
        n_customers, n_orders, TARGET_DB,
    )


if __name__ == "__main__":
    shop_etl_pipeline()
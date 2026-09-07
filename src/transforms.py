"""
Pure transformation functions.

ไม่มีการเชื่อมต่อ database หรือ I/O ใด ๆ
รับ DataFrame เข้า -> คืน DataFrame ออก จึง unit test ได้ด้วย dummy data
"""

import re
import pandas as pd

DEFAULT_EMAIL = "unknown@domain.com"
DEFAULT_CURRENCY = "USD"
DEFAULT_RATE = 1.0


def normalize_phone(phone) -> str | None:
    """คงไว้เฉพาะตัวเลข ถ้าไม่เหลือตัวเลขเลยคืน None"""
    if phone is None or pd.isna(phone):
        return None
    digits = re.sub(r"\D", "", str(phone))
    return digits if digits else None


def fill_missing_email(email) -> str:
    """แทนอีเมลที่ว่าง/NULL ด้วย placeholder และแปลงเป็นตัวพิมพ์เล็ก"""
    if email is None or pd.isna(email) or str(email).strip() == "":
        return DEFAULT_EMAIL
    return str(email).strip().lower()


def clean_customers(df: pd.DataFrame) -> pd.DataFrame:
    """normalize phone/email แล้วลบข้อมูลซ้ำ โดยเก็บ signup_date ล่าสุด"""
    out = df.copy()
    out["phone"] = out["phone"].apply(normalize_phone)
    out["email"] = out["email"].apply(fill_missing_email)
    out["signup_date"] = pd.to_datetime(out["signup_date"], errors="coerce")

    out = (
        out.sort_values("signup_date", ascending=False, na_position="last")
           .drop_duplicates(subset="customer_id", keep="first")
           .sort_values("customer_id")
           .reset_index(drop=True)
    )
    return out


def filter_invalid_orders(df: pd.DataFrame) -> pd.DataFrame:
    """ตัด order ที่ total_amount เป็น NULL, 0 หรือติดลบออก"""
    out = df.copy()
    out["total_amount"] = pd.to_numeric(out["total_amount"], errors="coerce")
    return out[out["total_amount"] > 0].reset_index(drop=True)


def convert_to_usd(orders: pd.DataFrame, rates: pd.DataFrame) -> pd.DataFrame:
    """แปลงยอดเงินเป็น USD

    จับคู่ด้วย (currency, date) ถ้าหา rate ไม่เจอใช้ rate = 1.0 ตามที่โจทย์กำหนด
    และติด flag fx_rate_matched ไว้ตรวจสอบภายหลัง
    currency ที่เป็น NULL ถือเป็น USD
    """
    o = orders.copy()
    r = rates.copy()

    o["currency"] = o["currency"].fillna(DEFAULT_CURRENCY)
    o["_join_date"] = pd.to_datetime(o["order_date"], errors="coerce").dt.strftime("%Y-%m-%d")

    if r.empty:
        o["rate_to_usd"] = pd.NA
    else:
        r["_join_date"] = pd.to_datetime(r["date"], errors="coerce").dt.strftime("%Y-%m-%d")
        r = r[["currency", "_join_date", "rate_to_usd"]].drop_duplicates(
            subset=["currency", "_join_date"], keep="last"
        )
        o = o.merge(r, on=["currency", "_join_date"], how="left")

    o["fx_rate_matched"] = o["rate_to_usd"].notna()
    o["rate_to_usd"] = pd.to_numeric(o["rate_to_usd"], errors="coerce").fillna(DEFAULT_RATE)
    o["amount_usd"] = (o["total_amount"] * o["rate_to_usd"]).round(2)

    return o.drop(columns="_join_date")
"""Unit tests สำหรับ transformation logic — ใช้ dummy data ไม่ต้องต่อ database"""

import pandas as pd
import pytest

from src.transforms import (
    DEFAULT_EMAIL,
    clean_customers,
    convert_to_usd,
    fill_missing_email,
    filter_invalid_orders,
    normalize_phone,
)


@pytest.mark.parametrize("raw, expected", [
    ("+1 (555) 123-4567", "15551234567"),
    ("555-987-6543",      "5559876543"),
    ("+44 20 7123 1234",  "442071231234"),
    ("1-800-555-DINO",    "1800555"),
    ("Ext 444",           "444"),
    ("abc",               None),
    (None,                None),
])
def test_normalize_phone(raw, expected):
    assert normalize_phone(raw) == expected


def test_fill_missing_email_replaces_null_and_blank():
    assert fill_missing_email(None) == DEFAULT_EMAIL
    assert fill_missing_email("   ") == DEFAULT_EMAIL


def test_fill_missing_email_normalizes_case():
    assert fill_missing_email("  Alice@Example.COM ") == "alice@example.com"


def test_clean_customers_keeps_latest_signup_date():
    df = pd.DataFrame({
        "customer_id": [2, 2],
        "full_name":   ["Bob Jones", "Bob Jones"],
        "email":       [None, "bob.jones@example.com"],
        "phone":       ["555-987-6543", "555-987-6543"],
        "signup_date": ["2023-02-20", "2023-09-15"],
    })
    out = clean_customers(df)

    assert len(out) == 1
    assert out.iloc[0]["email"] == "bob.jones@example.com"


def test_clean_customers_applies_phone_and_email_rules():
    df = pd.DataFrame({
        "customer_id": [8],
        "full_name":   ["Hannah Abbott"],
        "email":       [None],
        "phone":       ["+1 (555) 000-1111"],
        "signup_date": ["2023-07-01"],
    })
    out = clean_customers(df)

    assert out.iloc[0]["phone"] == "15550001111"
    assert out.iloc[0]["email"] == DEFAULT_EMAIL


def test_clean_customers_keeps_distinct_customers():
    df = pd.DataFrame({
        "customer_id": [1, 2],
        "full_name":   ["Alice Smith", "Bob Jones"],
        "email":       ["a@x.com", "b@x.com"],
        "phone":       ["5551234567", "5559876543"],
        "signup_date": ["2023-01-15", "2023-02-20"],
    })
    assert len(clean_customers(df)) == 2


def test_filter_invalid_orders_removes_non_positive_amounts():
    df = pd.DataFrame({
        "order_id":     [101, 103, 114, 999],
        "total_amount": [150.0, -50.0, 0.0, None],
    })
    out = filter_invalid_orders(df)

    assert out["order_id"].tolist() == [101]


def test_convert_to_usd_applies_matching_rate():
    orders = pd.DataFrame({
        "order_id": [102], "order_date": ["2023-05-01"],
        "total_amount": [200.0], "currency": ["EUR"],
    })
    rates = pd.DataFrame({
        "currency": ["EUR"], "date": ["2023-05-01"], "rate_to_usd": [1.10],
    })
    out = convert_to_usd(orders, rates)

    assert out.iloc[0]["amount_usd"] == 220.0
    assert bool(out.iloc[0]["fx_rate_matched"]) is True


def test_convert_to_usd_falls_back_when_rate_missing():
    orders = pd.DataFrame({
        "order_id": [115], "order_date": ["2023-05-10"],
        "total_amount": [25000.0], "currency": ["JPY"],
    })
    rates = pd.DataFrame({
        "currency": ["JPY"], "date": ["2023-05-03"], "rate_to_usd": [0.0069],
    })
    out = convert_to_usd(orders, rates)

    assert out.iloc[0]["rate_to_usd"] == 1.0
    assert bool(out.iloc[0]["fx_rate_matched"]) is False


def test_convert_to_usd_treats_null_currency_as_usd():
    orders = pd.DataFrame({
        "order_id": [107], "order_date": ["2023-05-05"],
        "total_amount": [120.0], "currency": [None],
    })
    rates = pd.DataFrame({
        "currency": ["EUR"], "date": ["2023-05-05"], "rate_to_usd": [1.105],
    })
    out = convert_to_usd(orders, rates)

    assert out.iloc[0]["currency"] == "USD"
    assert out.iloc[0]["amount_usd"] == 120.0
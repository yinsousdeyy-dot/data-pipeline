

import pytest

from src.transform.cleaner import OrderTransformer

@pytest.fixture
def transformer():
    return OrderTransformer()

def test_valid_record_transformation(transformer):
    raw_data = [ {
        "order_id" : "ord-001",
        "customer_id": 101,
        "customer_email": "  USER@EXAMPLE.COM  ",
        "amount": 99.50,
        "status": "completed",
        "order_timestamp": "2026-08-30T10:00:00"
    }]

    clean_df , quarantined = transformer.validate_and_clean(raw_data)

    assert len(quarantined) == 0 
    assert len(clean_df) ==1
    assert clean_df.iloc[0]["customer_email"] == "user@example.com"
    assert clean_df.iloc[0]["status"] == "COMPLETED"

def test_quarantine_negative_amount_invalid_email(transformer) :
    raw_data = [
        {
            "order_id": "ord-002",
            "customer_id": 102,
            "customer_email": "not-an-email",
            "amount": 50.0,
            "status": "COMPLETED",
            "order_timestamp": "2026-08-30T10:00:00"
        },
        {
            "order_id": "ord-003",
            "customer_id": 103,
            "customer_email": "valid@example.com",
            "amount": -100.0,  # Negative amount violation
            "status": "COMPLETED",
            "order_timestamp": "2026-08-30T10:00:00"
        }

    ]

    clean_df, quarantined = transformer.validate_and_clean(raw_data)

    assert len(clean_df) == 0
    assert len(quarantined) == 2

def test_deduplication_keeps_last(transformer):
    raw_data = [
        {
            "order_id": "duplicate-id",
            "customer_id": 101,
            "customer_email": "first@example.com",
            "amount": 10.0,
            "status": "PENDING",
            "order_timestamp": "2026-08-30T09:00:00"
        },
        {
            "order_id": "duplicate-id",
            "customer_id": 101,
            "customer_email": "second@example.com",
            "amount": 20.0,
            "status": "COMPLETED",
            "order_timestamp": "2026-08-30T10:00:00"
        }
    ]
    clean_df, quarantined = transformer.validate_and_clean(raw_data)
    
    assert len(clean_df) ==1
    assert clean_df.iloc[0]["amount"] == 20.0
    assert clean_df.iloc[0]["status"] == "COMPLETED"
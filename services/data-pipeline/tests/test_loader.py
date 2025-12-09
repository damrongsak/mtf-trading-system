import pytest
import pandas as pd
import numpy as np
from app.services.loader import load_candles_from_csv
import os

# Create a sample CSV for testing
@pytest.fixture
def valid_csv(tmp_path):
    d = tmp_path / "valid.csv"
    d.write_text("time,open,high,low,close,volume\n2023-01-01 00:00,100,105,95,102,1000")
    return str(d)

@pytest.fixture
def invalid_csv_schema(tmp_path):
    d = tmp_path / "invalid_schema.csv"
    d.write_text("time,price,volume\n2023-01-01 00:00,100,1000")
    return str(d)

@pytest.fixture
def invalid_csv_range(tmp_path):
    d = tmp_path / "invalid_range.csv"
    # High < Low (105 < 110) -> Invalid
    d.write_text("time,open,high,low,close,volume\n2023-01-01 00:00,100,105,110,102,1000")
    return str(d)

@pytest.fixture
def invalid_csv_negative(tmp_path):
    d = tmp_path / "invalid_neg.csv"
    # Negative Price
    d.write_text("time,open,high,low,close,volume\n2023-01-01 00:00,-100,105,95,102,1000")
    return str(d)

def test_load_valid_csv(valid_csv):
    df = load_candles_from_csv(valid_csv, "TEST", "1H")
    assert not df.empty
    assert df.iloc[0]['open'] == 100
    assert df.iloc[0]['symbol'] == "TEST"

def test_load_invalid_schema(invalid_csv_schema):
    with pytest.raises(ValueError, match="CSV missing required columns"):
        load_candles_from_csv(invalid_csv_schema, "TEST", "1H")

def test_load_invalid_range(invalid_csv_range):
    with pytest.raises(ValueError, match="High must be >= Low"):
        load_candles_from_csv(invalid_csv_range, "TEST", "1H")

def test_load_invalid_negative(invalid_csv_negative):
    with pytest.raises(ValueError, match="Prices cannot be negative"):
        load_candles_from_csv(invalid_csv_negative, "TEST", "1H")

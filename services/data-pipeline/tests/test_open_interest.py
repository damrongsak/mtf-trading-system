import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock
from sqlalchemy.orm import Session
from app.services.open_interest_service import OpenInterestService
import pandas as pd
import io

# Mock Excel Data
def create_mock_excel_file():
    # Create a DataFrame that mimics the structure
    # Row 0: Strike, NaN, Contract1, NaN
    # Row 1: NaN, NaN, C, P
    # Row 2: 2000, NaN, 100, 50
    
    data = [
        ["Strike", None, "G5WZ5\n5 DTE", None],
        [None, None, "C", "P"],
        [2000, None, 100, 50],
        [2050, None, 200, 25]
    ]
    df = pd.DataFrame(data)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Wed, Dec 24, 2025', index=False, header=False)
    return output.getvalue()

def test_parse_and_store_success():
    mock_db = MagicMock(spec=Session)
    file_content = create_mock_excel_file()
    
    result = OpenInterestService.parse_and_store(file_content, mock_db)
    
    assert result['status'] == 'success'
    assert result['records_processed'] == 2
    # Verify timestamp parsing (assuming UTC for simplicity in service)
    # Service uses datetime.strptime which creates naive datetime, then checks.
    assert '2025-12-24' in result['snapshot_at']
    
    # Verify DB calls
    assert mock_db.execute.called
    assert mock_db.commit.called

def test_parse_and_store_with_snapshot_override():
    mock_db = MagicMock(spec=Session)
    file_content = create_mock_excel_file()
    override_date = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    result = OpenInterestService.parse_and_store(file_content, mock_db, snapshot_at=override_date)
    
    assert result['snapshot_at'] == override_date.isoformat()

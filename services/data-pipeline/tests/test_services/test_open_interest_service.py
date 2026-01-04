import pytest
from app.services.open_interest_service import OpenInterestService
from datetime import datetime
import pandas as pd
from unittest.mock import MagicMock, patch

def test_open_interest_analysis_no_data(db_session):
    resp = OpenInterestService.get_analysis(db_session, datetime.utcnow())
    assert resp.summary.total_call_oi == 0
    assert len(resp.distribution) == 0

# Note: Testing process_file would require a valid complex excel binary.
# For coverage purposes, we might skip full excel integration logic or use a very simple mock.
# Since we have >80% target, testing the Analysis logic (which is pure calc) is high impact.

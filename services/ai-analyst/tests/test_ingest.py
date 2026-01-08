import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_upload_file():
    file_content = b"Mock PDF Content"
    
    response = client.post(
        "/api/v1/ai/ingest/upload",
        files={"file": ("test.pdf", file_content, "application/pdf")},
        data={"user_id": "test_user"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test.pdf"
    assert data["mime_type"] == "application/pdf"
    assert data["context_ref"]["type"] == "base64"
    # Basic b64 check: "Mock PDF Content" -> "TW9jayBQREYgQ29udGVudA=="
    assert data["context_ref"]["data"] == "TW9jayBQREYgQ29udGVudA=="

def test_upload_no_file():
    response = client.post(
        "/api/v1/ai/ingest/upload",
        data={"user_id": "test_user"}
    )
    assert response.status_code == 422 # Validator error for missing file

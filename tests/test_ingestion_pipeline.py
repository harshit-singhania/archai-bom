"""Tests for the integrated ingestion pipeline."""

import os
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.ingestion_pipeline import ingest_pdf

client = TestClient(app)

def test_ingest_pdf_integration():
    """Test ingestion pipeline function logic with real PDF."""
    pdf_path = "sample_pdfs/test_floorplan.pdf"
    
    # Check if the file exists for integration testing
    if not os.path.exists(pdf_path):
        pytest.skip(f"{pdf_path} not found")
        
    result = ingest_pdf(pdf_path)
    
    assert result.total_wall_count > 0
    assert len(result.wall_segments) == result.total_wall_count
    assert result.total_linear_pts > 0

def test_api_ingest_endpoint():
    """Test the /api/v1/ingest API endpoint."""
    pdf_path = "sample_pdfs/test_floorplan.pdf"
    
    if not os.path.exists(pdf_path):
        pytest.skip(f"{pdf_path} not found")
        
    with open(pdf_path, "rb") as f:
        response = client.post(
            "/api/v1/ingest", 
            files={"file": ("test_floorplan.pdf", f, "application/pdf")}
        )
        
    assert response.status_code == 200
    data = response.json()
    assert "total_wall_count" in data
    assert "wall_segments" in data
    assert data["total_wall_count"] > 0
    
def test_api_ingest_endpoint_invalid_file():
    """Test endpoint with non-PDF file."""
    response = client.post(
        "/api/v1/ingest", 
        files={"file": ("test_floorplan.txt", b"dummy content", "text/plain")}
    )
    
    assert response.status_code == 400
    assert "must be a PDF" in response.json()["detail"]

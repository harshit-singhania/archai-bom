"""API routes."""

import os
import tempfile
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from app.services.ingestion_pipeline import ingest_pdf

router = APIRouter()


@router.post("/v1/ingest")
async def ingest_floorplan(file: UploadFile = File(...)):
    """
    Ingest a PDF floorplan, extract vectors, and detect structural walls.
    
    Returns a JSON containing the wall count and explicit geometry 
    of wall segments.
    """
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
        
    try:
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", mode="wb") as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
            
        try:
            # Run ingestion pipeline
            result = ingest_pdf(tmp_path)
            return result.model_dump()
            
        except ValueError as e:
            # Catch ValueError when no vectors are found (e.g. scanned PDF)
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error handling file upload: {str(e)}")
    """
    Upload a PDF floorplan for processing.
    
    This is a placeholder endpoint. Full implementation will:
    1. Save the uploaded file
    2. Extract vector lines using PyMuPDF
    3. Return extracted geometry
    """
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    return JSONResponse(
        content={
            "message": "PDF upload endpoint - placeholder",
            "filename": file.filename,
            "status": "not_implemented"
        },
        status_code=200,
    )


@router.get("/pdf/status/{pdf_id}")
async def get_pdf_status(pdf_id: str):
    """Get processing status of a PDF."""
    return {"pdf_id": pdf_id, "status": "placeholder"}

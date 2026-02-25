"""API routes."""

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

router = APIRouter()


@router.post("/pdf/upload")
async def upload_pdf(file: UploadFile = File(...)):
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

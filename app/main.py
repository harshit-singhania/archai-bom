"""FastAPI main application entry point."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.routes import router as api_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="AI-powered Bill of Materials generator from architectural floorplans",
)

app.include_router(api_router, prefix="/api")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return JSONResponse(
        content={"status": "ok", "version": settings.VERSION},
        status_code=200,
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Welcome to ArchAI BOM API", "version": settings.VERSION}

"""Floorplan repository for database operations."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlmodel import select

from app.core.database import get_session
from app.models.database import Floorplan


def create_floorplan(
    pdf_storage_url: str,
    project_id: Optional[int] = None,
    raw_vector_data: Optional[Dict[str, Any]] = None,
    status: str = "uploaded",
) -> int:
    """Create a new floorplan record.

    Args:
        pdf_storage_url: URL or filename for the stored PDF
        project_id: Optional ID of the parent project (may be None for standalone ingest)
        raw_vector_data: Optional extracted vector data
        status: Initial status (uploaded, processing, processed, error)

    Returns:
        Created Floorplan ID
    """
    with get_session() as session:
        floorplan = Floorplan(
            project_id=project_id,
            pdf_storage_url=pdf_storage_url,
            raw_vector_data=raw_vector_data or {},
            status=status,
        )
        session.add(floorplan)
        session.commit()
        session.refresh(floorplan)
        return floorplan.id


def get_floorplan_by_id(floorplan_id: int) -> Optional[dict]:
    """Get a floorplan by ID.

    Args:
        floorplan_id: The floorplan ID

    Returns:
        Floorplan dict or None if not found
    """
    with get_session() as session:
        floorplan = session.get(Floorplan, floorplan_id)
        if floorplan:
            return {
                "id": floorplan.id,
                "project_id": floorplan.project_id,
                "pdf_storage_url": floorplan.pdf_storage_url,
                "raw_vector_data": floorplan.raw_vector_data,
                "status": floorplan.status,
                "error_message": floorplan.error_message,
                "created_at": floorplan.created_at.isoformat() if floorplan.created_at else None,
                "updated_at": floorplan.updated_at.isoformat() if floorplan.updated_at else None,
            }
        return None


def list_floorplans_by_project(project_id: int) -> List[dict]:
    """List all floorplans for a project.

    Args:
        project_id: The project ID

    Returns:
        List of Floorplan dicts
    """
    with get_session() as session:
        query = select(Floorplan).where(Floorplan.project_id == project_id)
        floorplans = session.exec(query).all()
        return [
            {
                "id": f.id,
                "project_id": f.project_id,
                "pdf_storage_url": f.pdf_storage_url,
                "raw_vector_data": f.raw_vector_data,
                "status": f.status,
                "error_message": f.error_message,
                "created_at": f.created_at.isoformat() if f.created_at else None,
                "updated_at": f.updated_at.isoformat() if f.updated_at else None,
            }
            for f in floorplans
        ]


def update_floorplan_status(floorplan_id: int, status: str) -> bool:
    """Update a floorplan's status.

    Args:
        floorplan_id: The floorplan ID
        status: New status value (uploaded, processing, processed, error)

    Returns:
        True if updated, False if not found
    """
    with get_session() as session:
        floorplan = session.get(Floorplan, floorplan_id)
        if floorplan:
            floorplan.status = status
            floorplan.updated_at = datetime.utcnow()
            session.add(floorplan)
            session.commit()
            return True
        return False


def update_floorplan_error(floorplan_id: int, error_message: str) -> bool:
    """Mark a floorplan as errored with an error message.

    Args:
        floorplan_id: The floorplan ID
        error_message: Human-readable error description

    Returns:
        True if updated, False if not found
    """
    with get_session() as session:
        floorplan = session.get(Floorplan, floorplan_id)
        if floorplan:
            floorplan.status = "error"
            floorplan.error_message = error_message
            floorplan.updated_at = datetime.utcnow()
            session.add(floorplan)
            session.commit()
            return True
        return False


def update_floorplan_vector_data(
    floorplan_id: int, raw_vector_data: Dict[str, Any]
) -> bool:
    """Update a floorplan's extracted vector data.

    Args:
        floorplan_id: The floorplan ID
        raw_vector_data: Extracted vector data from PDF

    Returns:
        True if updated, False if not found
    """
    with get_session() as session:
        floorplan = session.get(Floorplan, floorplan_id)
        if floorplan:
            floorplan.raw_vector_data = raw_vector_data
            floorplan.updated_at = datetime.utcnow()
            session.add(floorplan)
            session.commit()
            return True
        return False

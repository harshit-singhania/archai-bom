"""Floorplan repository for database operations."""

from typing import Optional, List, Dict, Any
from sqlmodel import select

from app.core.database import get_session
from app.models.database import Floorplan


def create_floorplan(
    project_id: int,
    pdf_storage_url: str,
    raw_vector_data: Optional[Dict[str, Any]] = None,
    status: str = "uploaded",
) -> int:
    """Create a new floorplan.

    Args:
        project_id: ID of the parent project
        pdf_storage_url: URL to the stored PDF
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
            session.add(floorplan)
            session.commit()
            return True
        return False

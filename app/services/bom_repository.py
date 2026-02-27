"""Generated BOM repository for database operations."""

from typing import Optional, List, Dict, Any
from sqlmodel import select

from app.core.database import get_session
from app.models.database import GeneratedBOM


def create_bom(
    floorplan_id: int, total_cost_inr: float, bom_data: Optional[Dict[str, Any]] = None
) -> int:
    """Create a new generated BOM.

    Args:
        floorplan_id: ID of the parent floorplan
        total_cost_inr: Total cost in Indian Rupees
        bom_data: Optional BOM line items and metadata

    Returns:
        Created GeneratedBOM ID
    """
    with get_session() as session:
        bom = GeneratedBOM(
            floorplan_id=floorplan_id,
            total_cost_inr=total_cost_inr,
            bom_data=bom_data or {},
        )
        session.add(bom)
        session.commit()
        session.refresh(bom)
        return bom.id


def get_bom_by_id(bom_id: int) -> Optional[dict]:
    """Get a BOM by ID.

    Args:
        bom_id: The BOM ID

    Returns:
        GeneratedBOM dict or None if not found
    """
    with get_session() as session:
        bom = session.get(GeneratedBOM, bom_id)
        if bom:
            return {
                "id": bom.id,
                "floorplan_id": bom.floorplan_id,
                "total_cost_inr": bom.total_cost_inr,
                "bom_data": bom.bom_data,
                "created_at": bom.created_at.isoformat() if bom.created_at else None,
            }
        return None


def get_bom_by_floorplan(floorplan_id: int) -> Optional[dict]:
    """Get the most recent BOM for a specific floorplan.

    Args:
        floorplan_id: The floorplan ID

    Returns:
        GeneratedBOM dict or None if not found
    """
    with get_session() as session:
        query = select(GeneratedBOM).where(GeneratedBOM.floorplan_id == floorplan_id)
        bom = session.exec(query).first()
        if bom:
            return {
                "id": bom.id,
                "floorplan_id": bom.floorplan_id,
                "total_cost_inr": bom.total_cost_inr,
                "bom_data": bom.bom_data,
                "created_at": bom.created_at.isoformat() if bom.created_at else None,
            }
        return None


def list_boms_by_project(project_id: int) -> List[dict]:
    """List all BOMs for a project (via floorplans).

    Args:
        project_id: The project ID

    Returns:
        List of GeneratedBOM dicts
    """
    from app.models.database import Floorplan

    with get_session() as session:
        # Get all floorplan IDs for this project
        floorplan_query = select(Floorplan.id).where(Floorplan.project_id == project_id)
        floorplan_ids = [row[0] for row in session.exec(floorplan_query).all()]

        if not floorplan_ids:
            return []

        # Get all BOMs for these floorplans
        bom_query = select(GeneratedBOM).where(
            GeneratedBOM.floorplan_id.in_(floorplan_ids)
        )
        boms = session.exec(bom_query).all()
        return [
            {
                "id": b.id,
                "floorplan_id": b.floorplan_id,
                "total_cost_inr": b.total_cost_inr,
                "bom_data": b.bom_data,
                "created_at": b.created_at.isoformat() if b.created_at else None,
            }
            for b in boms
        ]


def update_bom_data(
    bom_id: int, total_cost_inr: float, bom_data: Dict[str, Any]
) -> bool:
    """Update a BOM's data.

    Args:
        bom_id: The BOM ID
        total_cost_inr: Updated total cost
        bom_data: Updated BOM line items and metadata

    Returns:
        True if updated, False if not found
    """
    with get_session() as session:
        bom = session.get(GeneratedBOM, bom_id)
        if bom:
            bom.total_cost_inr = total_cost_inr
            bom.bom_data = bom_data
            session.add(bom)
            session.commit()
            return True
        return False

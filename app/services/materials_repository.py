"""Material pricing repository for BOM calculator inputs."""

from typing import Any

from sqlmodel import select

from app.core.database import get_session
from app.models.database import MaterialPricing


def get_all_materials() -> list[dict[str, Any]]:
    """Load all materials from the pricing catalog."""
    with get_session() as session:
        materials = session.exec(select(MaterialPricing)).all()
        return [_serialize_material(material) for material in materials]


def get_materials_by_category(category: str) -> list[dict[str, Any]]:
    """Load materials filtered by category."""
    with get_session() as session:
        query = select(MaterialPricing).where(MaterialPricing.category == category)
        materials = session.exec(query).all()
        return [_serialize_material(material) for material in materials]


def _serialize_material(material: MaterialPricing) -> dict[str, Any]:
    """Convert MaterialPricing row into repository dict contract."""
    return {
        "id": material.id,
        "material_name": material.material_name,
        "category": material.category,
        "unit_of_measurement": material.unit_of_measurement,
        "cost_inr": material.cost_inr,
    }

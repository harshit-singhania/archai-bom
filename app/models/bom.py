"""Pydantic BOM domain models and deterministic calculation constants."""

from enum import Enum

from pydantic import BaseModel, Field


class MaterialCategory(str, Enum):
    """Supported pricing catalog categories for deterministic BOM mapping."""

    WALL = "wall"
    FLOORING = "flooring"
    CEILING = "ceiling"
    DOOR = "door"
    DOOR_HARDWARE = "door_hardware"
    PAINT = "paint"
    ELECTRICAL = "electrical"
    BASEBOARD = "baseboard"
    WATERPROOFING = "waterproofing"
    SPECIALTY = "specialty"


class MaterialInfo(BaseModel):
    """Material catalog row used by the pure BOM calculator."""

    material_name: str = Field(..., description="Human-readable material name")
    category: str = Field(..., description="Material category key")
    unit_of_measurement: str = Field(
        ..., description="Quantity unit such as sqft, running_foot, piece"
    )
    cost_inr: float = Field(..., ge=0, description="Installed unit rate in INR")


class BOMLineItem(BaseModel):
    """One priced line item in the generated bill of materials."""

    material_name: str = Field(..., description="Material selected for this line")
    category: str = Field(..., description="Category used to select material")
    quantity: float = Field(
        ..., ge=0, description="Computed quantity in line-item unit"
    )
    unit: str = Field(..., description="Unit for quantity and rate")
    rate_inr: float = Field(..., ge=0, description="Rate in INR per unit")
    amount_inr: float = Field(..., ge=0, description="Line amount in INR")
    room_name: str | None = Field(
        default=None,
        description="Room that triggered this line item when room-scoped",
    )
    notes: str | None = Field(
        default=None,
        description="Optional notes about assumptions or special handling",
    )


class BOMResult(BaseModel):
    """Final deterministic BOM payload for persistence and API responses."""

    line_items: list[BOMLineItem] = Field(
        default_factory=list,
        description="All priced material line items",
    )
    grand_total_inr: float = Field(..., ge=0, description="Grand total in INR")
    room_count: int = Field(..., ge=0, description="Number of rooms in the layout")
    total_area_sqm: float = Field(
        ..., ge=0, description="Total room area in square meters"
    )


DEFAULT_CEILING_HEIGHT_MM: float = 2700.0
SQM_TO_SQFT: float = 10.764
M_TO_FT: float = 3.281
MM_TO_M: float = 0.001

BASE_ROOM_CATEGORIES: list[str] = [
    MaterialCategory.FLOORING.value,
    MaterialCategory.CEILING.value,
    MaterialCategory.PAINT.value,
    MaterialCategory.ELECTRICAL.value,
    MaterialCategory.BASEBOARD.value,
]
BASE_WALL_CATEGORIES: list[str] = [MaterialCategory.WALL.value]
BASE_DOOR_CATEGORIES: list[str] = [
    MaterialCategory.DOOR.value,
    MaterialCategory.DOOR_HARDWARE.value,
]

ROOM_TYPE_MATERIALS: dict[str, list[str]] = {
    "bathroom": [MaterialCategory.WATERPROOFING.value],
    "washroom": [MaterialCategory.WATERPROOFING.value],
    "restroom": [MaterialCategory.WATERPROOFING.value],
    "toilet": [MaterialCategory.WATERPROOFING.value],
    "kitchen": [MaterialCategory.SPECIALTY.value],
    "pantry": [MaterialCategory.SPECIALTY.value],
    "server_room": [MaterialCategory.SPECIALTY.value],
    "server": [MaterialCategory.SPECIALTY.value],
    "lab": [MaterialCategory.SPECIALTY.value],
}

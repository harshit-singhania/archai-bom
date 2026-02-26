"""Pydantic models for generated interior layouts."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class InteriorWall(BaseModel):
    """An interior partition wall in real-world millimeters."""

    id: str = Field(..., description="Interior wall identifier (e.g. iw_1)")
    x1: float = Field(..., description="Start X coordinate in mm")
    y1: float = Field(..., description="Start Y coordinate in mm")
    x2: float = Field(..., description="End X coordinate in mm")
    y2: float = Field(..., description="End Y coordinate in mm")
    thickness_mm: float = Field(default=100.0, gt=0, description="Wall thickness in mm")
    material: str = Field(
        default="drywall", min_length=1, description="Wall material key"
    )


class Door(BaseModel):
    """A door opening anchored on an interior or perimeter wall."""

    id: str = Field(..., description="Door identifier (e.g. d_1)")
    wall_id: str = Field(..., description="Referenced wall id")
    position_along_wall: float = Field(
        ..., ge=0.0, le=1.0, description="Door position as wall-length fraction"
    )
    width_mm: float = Field(..., gt=0, description="Door width in mm")
    swing_direction: Literal["left", "right", "sliding"] = Field(
        ..., description="Door swing direction"
    )
    door_type: Literal["single", "double", "sliding"] = Field(
        ..., description="Door type"
    )


class Fixture(BaseModel):
    """A room fixture element."""

    id: str = Field(..., description="Fixture identifier (e.g. f_1)")
    room_name: str = Field(..., min_length=1, description="Owning room name")
    fixture_type: str = Field(..., min_length=1, description="Fixture category")
    center_x: float = Field(..., description="Fixture center X in mm")
    center_y: float = Field(..., description="Fixture center Y in mm")
    width_mm: float = Field(..., gt=0, description="Fixture width in mm")
    depth_mm: float = Field(..., gt=0, description="Fixture depth in mm")
    rotation_deg: float = Field(
        ..., ge=0, le=360, description="Fixture rotation in degrees"
    )


class GeneratedRoom(BaseModel):
    """A generated room polygon and metadata."""

    name: str = Field(..., min_length=1, description="Room name")
    room_type: str = Field(..., min_length=1, description="Room type")
    boundary: list[tuple[float, float]] = Field(
        ..., min_length=4, description="Closed polygon vertices in mm"
    )
    area_sqm: float = Field(..., gt=0, description="Room area in square meters")

    @field_validator("boundary")
    @classmethod
    def validate_closed_boundary(
        cls, value: list[tuple[float, float]]
    ) -> list[tuple[float, float]]:
        if value[0] != value[-1]:
            raise ValueError(
                "boundary must be closed (first and last points must match)"
            )
        return value


class GeneratedLayout(BaseModel):
    """Full generated layout DSL payload."""

    rooms: list[GeneratedRoom] = Field(default_factory=list)
    interior_walls: list[InteriorWall] = Field(default_factory=list)
    doors: list[Door] = Field(default_factory=list)
    fixtures: list[Fixture] = Field(default_factory=list)
    grid_size_mm: int = Field(default=50, gt=0)
    prompt: str = Field(..., min_length=1)
    perimeter_walls: list[dict[str, Any]] = Field(default_factory=list)
    page_dimensions_mm: tuple[float, float] = Field(
        ..., description="(width, height) in mm"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "rooms": [
                    {
                        "name": "Operatory 1",
                        "room_type": "operatory",
                        "boundary": [
                            [0.0, 0.0],
                            [3000.0, 0.0],
                            [3000.0, 3200.0],
                            [0.0, 3200.0],
                            [0.0, 0.0],
                        ],
                        "area_sqm": 9.6,
                    }
                ],
                "interior_walls": [
                    {
                        "id": "iw_1",
                        "x1": 3000.0,
                        "y1": 0.0,
                        "x2": 3000.0,
                        "y2": 6000.0,
                        "thickness_mm": 100.0,
                        "material": "drywall",
                    }
                ],
                "doors": [
                    {
                        "id": "d_1",
                        "wall_id": "iw_1",
                        "position_along_wall": 0.5,
                        "width_mm": 900.0,
                        "swing_direction": "left",
                        "door_type": "single",
                    }
                ],
                "fixtures": [
                    {
                        "id": "f_1",
                        "room_name": "Operatory 1",
                        "fixture_type": "dental_chair",
                        "center_x": 1500.0,
                        "center_y": 1600.0,
                        "width_mm": 1000.0,
                        "depth_mm": 2200.0,
                        "rotation_deg": 90.0,
                    }
                ],
                "grid_size_mm": 50,
                "prompt": "6 operatory dental clinic with reception",
                "perimeter_walls": [
                    {
                        "id": "perimeter_1",
                        "x1": 0.0,
                        "y1": 0.0,
                        "x2": 10000.0,
                        "y2": 0.0,
                        "thickness_mm": 200.0,
                    }
                ],
                "page_dimensions_mm": [10000.0, 8000.0],
            }
        }
    )

    @field_validator("page_dimensions_mm")
    @classmethod
    def validate_page_dimensions(
        cls, value: tuple[float, float]
    ) -> tuple[float, float]:
        width, height = value
        if width <= 0 or height <= 0:
            raise ValueError(
                "page_dimensions_mm must contain positive width and height"
            )
        return value

    def to_json(self) -> dict[str, Any]:
        """Return a JSON-serializable dictionary."""

        return self.model_dump(mode="json")

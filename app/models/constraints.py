"""Constraint checking models for generated layouts."""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class ConstraintViolationType(str, Enum):
    """Supported constraint violation categories."""

    ROOM_OVERLAP = "ROOM_OVERLAP"
    CORRIDOR_TOO_NARROW = "CORRIDOR_TOO_NARROW"
    DOOR_SWING_BLOCKED = "DOOR_SWING_BLOCKED"
    ROOM_NOT_ENCLOSED = "ROOM_NOT_ENCLOSED"
    AREA_EXCEEDS_PERIMETER = "AREA_EXCEEDS_PERIMETER"
    FIXTURE_OUTSIDE_ROOM = "FIXTURE_OUTSIDE_ROOM"
    FIXTURE_OVERLAP = "FIXTURE_OVERLAP"


class ConstraintViolation(BaseModel):
    """A single spatial rule violation."""

    type: ConstraintViolationType
    description: str = Field(..., min_length=1)
    severity: Literal["error", "warning"]
    affected_elements: list[str] = Field(default_factory=list)


class ConstraintResult(BaseModel):
    """Aggregate result of constraint validation."""

    passed: bool
    violations: list[ConstraintViolation] = Field(default_factory=list)
    summary: str

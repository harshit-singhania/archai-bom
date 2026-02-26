"""Models for layout generation pipeline results."""

from pydantic import BaseModel, Field

from app.models.constraints import ConstraintResult
from app.models.layout import GeneratedLayout


class GenerationResult(BaseModel):
    """Result of the self-correcting layout generation loop."""

    layout: GeneratedLayout | None = None
    success: bool
    iterations_used: int = Field(..., ge=0)
    constraint_history: list[ConstraintResult] = Field(default_factory=list)
    error_message: str | None = None

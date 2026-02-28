"""SQLModel database models for Supabase PostgreSQL."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import JSON, Text


class Project(SQLModel, table=True):
    """A construction/renovation project."""

    __tablename__ = "projects"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    project_name: str
    client_name: str
    status: str = Field(default="active")  # active, completed, archived

    # Relationships
    floorplans: List["Floorplan"] = Relationship(back_populates="project")


class Floorplan(SQLModel, table=True):
    """A floorplan PDF uploaded for a project."""

    __tablename__ = "floorplans"

    id: Optional[int] = Field(default=None, primary_key=True)
    # project_id is nullable to support standalone ingest without a project context
    project_id: Optional[int] = Field(
        default=None, foreign_key="projects.id", nullable=True
    )
    pdf_storage_url: str  # Supabase Storage URL or original filename
    raw_vector_data: Dict[str, Any] = Field(
        default_factory=dict, sa_type=JSON
    )  # PyMuPDF extracted lines
    status: str = Field(default="uploaded")  # uploaded, processing, processed, error
    error_message: Optional[str] = Field(
        default=None
    )  # Error details when status='error'
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    project: Optional[Project] = Relationship(back_populates="floorplans")
    boms: List["GeneratedBOM"] = Relationship(back_populates="floorplan")


class MaterialPricing(SQLModel, table=True):
    """Material pricing catalog for Indian market."""

    __tablename__ = "materials_pricing"

    id: Optional[int] = Field(default=None, primary_key=True)
    material_name: str
    unit_of_measurement: str  # sqft, running_foot, piece, etc.
    cost_inr: float  # Cost in Indian Rupees
    category: str = Field(default="uncategorized")  # wall, flooring, ceiling, etc.


class GeneratedBOM(SQLModel, table=True):
    """Generated Bill of Materials for a floorplan."""

    __tablename__ = "generated_boms"

    id: Optional[int] = Field(default=None, primary_key=True)
    floorplan_id: int = Field(foreign_key="floorplans.id")
    total_cost_inr: float
    bom_data: Dict[str, Any] = Field(
        default_factory=dict, sa_type=JSON
    )  # Final calculated line items
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    floorplan: Optional[Floorplan] = Relationship(back_populates="boms")


class AsyncJob(SQLModel, table=True):
    """Durable async job record for ingest and generation workloads.

    Tracks lifecycle transitions (queued -> running -> succeeded | failed)
    across process boundaries (API process and queue worker process).
    """

    __tablename__ = "async_jobs"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Job classification
    job_type: str  # "ingest" or "generate"

    # Status lifecycle: queued -> running -> succeeded | failed
    status: str = Field(default="queued")

    # Optional reference to the originating floorplan
    floorplan_id: Optional[int] = Field(
        default=None, foreign_key="floorplans.id", nullable=True
    )

    # Serialized job payload (JSON-encoded string for cross-process portability)
    payload: Optional[str] = Field(default=None, sa_type=Text)

    # Error details populated on failure
    error_message: Optional[str] = Field(default=None, sa_type=Text)

    # Result references populated on success
    # Stores result_type and result_id so callers can fetch the real record
    result_ref: Optional[Dict[str, Any]] = Field(default=None, sa_type=JSON)

    # Lifecycle timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = Field(default=None)
    finished_at: Optional[datetime] = Field(default=None)

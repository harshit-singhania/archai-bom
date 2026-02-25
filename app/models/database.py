"""SQLModel database models for Supabase PostgreSQL."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import JSON


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
    project_id: int = Field(foreign_key="projects.id")
    pdf_storage_url: str  # Supabase Storage URL
    raw_vector_data: Dict[str, Any] = Field(default_factory=dict, sa_type=JSON)  # PyMuPDF extracted lines
    status: str = Field(default="uploaded")  # uploaded, processing, processed, error
    
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


class GeneratedBOM(SQLModel, table=True):
    """Generated Bill of Materials for a floorplan."""
    __tablename__ = "generated_boms"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    floorplan_id: int = Field(foreign_key="floorplans.id")
    total_cost_inr: float
    bom_data: Dict[str, Any] = Field(default_factory=dict, sa_type=JSON)  # Final calculated line items
    
    # Relationships
    floorplan: Optional[Floorplan] = Relationship(back_populates="boms")
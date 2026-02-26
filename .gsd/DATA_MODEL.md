# DATA_MODEL.md — Database Schema

> **Database**: Supabase PostgreSQL
> **ORM**: SQLModel
> **Updated**: 2026-02-25

---

## Overview

Four core tables support the ArchAI BOM workflow:

1. **projects** — Client projects (e.g., "TechStart Office Fit-out")
2. **floorplans** — PDF floorplans uploaded for each project
3. **materials_pricing** — Indian market material rates (hardcoded for MVP)
4. **generated_boms** — Calculated Bills of Materials per floorplan

---

## Entity Relationship Diagram

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    projects     │────▶│   floorplans    │────▶│  generated_boms │
├─────────────────┤ 1:M ├─────────────────┤ 1:M ├─────────────────┤
│ id (PK)         │     │ id (PK)         │     │ id (PK)         │
│ created_at      │     │ project_id (FK) │     │ floorplan_id(FK)│
│ project_name    │     │ pdf_storage_url │     │ total_cost_inr  │
│ client_name     │     │ raw_vector_data │     │ bom_data (JSONB)│
│ status          │     │ status          │     └─────────────────┘
└─────────────────┘     └─────────────────┘
                                │
                                │ M:1 (reference)
                                ▼
                       ┌─────────────────┐
                       │materials_pricing│
                       ├─────────────────┤
                       │ id (PK)         │
                       │ material_name   │
                       │ unit_of_measurement│
                       │ cost_inr        │
                       └─────────────────┘
```

---

## Table Definitions

### projects

A construction/renovation project for a client.

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL PK | Auto-increment primary key |
| `created_at` | TIMESTAMP | Creation timestamp (UTC) |
| `project_name` | VARCHAR | Project name (e.g., "TechStart Office Fit-out") |
| `client_name` | VARCHAR | Client company name |
| `status` | VARCHAR | `active`, `completed`, or `archived` |

**Relationships:**
- One-to-Many with `floorplans`

---

### floorplans

A floorplan PDF uploaded for processing.

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL PK | Auto-increment primary key |
| `project_id` | INTEGER FK | Reference to parent project |
| `pdf_storage_url` | VARCHAR | Supabase Storage URL to the PDF file |
| `raw_vector_data` | JSONB | PyMuPDF extracted lines and metadata |
| `status` | VARCHAR | `uploaded`, `processing`, `processed`, `error` |

**JSONB Schema for `raw_vector_data`:**
```json
{
  "lines": 127,
  "page_dimensions": [612, 792],
  "extracted_at": "2026-02-25T10:30:00Z",
  "wall_types": ["outer", "interior", "partition"],
  "rooms_detected": ["reception", "workspace", "meeting_room", "pantry"],
  "vector_lines": [
    {"x1": 100, "y1": 100, "x2": 500, "y2": 100, "width": 3.0}
  ]
}
```

**Relationships:**
- Many-to-One with `projects`
- One-to-Many with `generated_boms`

---

### materials_pricing

Material pricing catalog for Indian market (MVP starter set).

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL PK | Auto-increment primary key |
| `material_name` | VARCHAR | Material description |
| `unit_of_measurement` | VARCHAR | `sqft`, `running_foot`, `piece`, etc. |
| `cost_inr` | DECIMAL | Price in Indian Rupees |

**Default Materials (10 items):**

| Material | Unit | Cost (₹) |
|----------|------|----------|
| Standard Gypsum Drywall (12mm) | sqft | 45.00 |
| Moisture-Resistant Drywall (12mm) | sqft | 65.00 |
| Tempered Glass Partition (10mm) | sqft | 350.00 |
| Laminated Glass Partition (12mm) | sqft | 450.00 |
| Vitrified Tiles (600x600mm) | sqft | 85.00 |
| Ceramic Wall Tiles (300x600mm) | sqft | 55.00 |
| Premium Vinyl Flooring (2mm) | sqft | 120.00 |
| Engineered Wood Flooring | sqft | 250.00 |
| Aluminum Door Frame | running_foot | 180.00 |
| HDF Flush Door (35mm) | piece | 4,500.00 |

---

### generated_boms

Generated Bill of Materials for a floorplan.

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL PK | Auto-increment primary key |
| `floorplan_id` | INTEGER FK | Reference to parent floorplan |
| `total_cost_inr` | DECIMAL | Total calculated cost |
| `bom_data` | JSONB | Line items and calculation details |

**JSONB Schema for `bom_data`:**
```json
{
  "generated_at": "2026-02-25T10:35:00Z",
  "line_items": [
    {
      "material": "Standard Gypsum Drywall (12mm)",
      "quantity": 450,
      "unit": "sqft",
      "rate": 45,
      "amount": 20250
    }
  ],
  "summary": {
    "total_area_sqft": 2000,
    "room_count": 4,
    "labor_estimate_inr": 250000
  }
}
```

**Relationships:**
- Many-to-One with `floorplans`

---

## SQLModel Implementation

Models are defined in `app/models/database.py`:

```python
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, Dict, Any
from datetime import datetime

class Project(SQLModel, table=True):
    __tablename__ = "projects"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    project_name: str
    client_name: str
    status: str = Field(default="active")
    
    floorplans: List["Floorplan"] = Relationship(back_populates="project")
```

See `app/models/database.py` for full implementation.

---

## Setup Script

Run to create schema and seed data:

```bash
python scripts/setup_supabase_schema.py
```

This script:
1. Connects to Supabase PostgreSQL using credentials from `.env`
2. Creates all 4 tables using SQLModel metadata
3. Seeds `materials_pricing` with 10 default materials
4. Creates a sample project with floorplan and BOM for testing

---

## Environment Variables

Required in `.env`:

```bash
SUPABASE_PROJECT_URL=https://your-project.supabase.co
SUPABASE_PUBLISHABLE_KEY=your-anon-key
SUPABASE_PASSWORD=your-db-password
```

---

## Usage Examples

### Insert a new project
```python
from app.models.database import Project
from app.core.supabase import get_supabase

supabase = get_supabase()
project = Project(project_name="New Office", client_name="Acme Corp")

# Using Supabase client
data = project.model_dump(exclude_unset=True)
result = supabase.table("projects").insert(data).execute()
```

### Query with relationships
```python
# Get project with all floorplans
result = supabase.table("projects").select(
    "*, floorplans(*)"
).eq("id", 1).execute()
```

---

## Future Enhancements

- **RLS (Row Level Security)**: Enable per-user data isolation
- **Real-time subscriptions**: Live BOM updates via Supabase realtime
- **Storage buckets**: Organize PDFs by project
- **Audit logging**: Track who modified what and when

#!/usr/bin/env python3
"""
Setup Supabase schema and seed data.

This script:
1. Creates the database tables using SQLModel
2. Seeds materials_pricing with 45 categorized materials
3. Creates sample project with floorplan and BOM

Usage:
    python scripts/setup_supabase_schema.py
"""

import os
import sys
from collections import Counter
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import SQLModel, create_engine, Session, select
from app.core.config import settings
from app.models.database import Project, Floorplan, MaterialPricing, GeneratedBOM


# Hardcoded materials for Indian market (MVP catalog, Feb 2026)
DEFAULT_MATERIALS = [
    # Wall (7)
    {
        "material_name": "Standard Gypsum Drywall (12mm)",
        "unit_of_measurement": "sqft",
        "cost_inr": 48.0,
        "category": "wall",
    },
    {
        "material_name": "Moisture-Resistant Drywall (12mm)",
        "unit_of_measurement": "sqft",
        "cost_inr": 68.0,
        "category": "wall",
    },
    {
        "material_name": "Tempered Glass Partition (10mm)",
        "unit_of_measurement": "sqft",
        "cost_inr": 380.0,
        "category": "wall",
    },
    {
        "material_name": "Laminated Glass Partition (12mm)",
        "unit_of_measurement": "sqft",
        "cost_inr": 520.0,
        "category": "wall",
    },
    {
        "material_name": "AAC Block Partition (100mm)",
        "unit_of_measurement": "sqft",
        "cost_inr": 58.0,
        "category": "wall",
    },
    {
        "material_name": "Cement Board Partition (8mm)",
        "unit_of_measurement": "sqft",
        "cost_inr": 42.0,
        "category": "wall",
    },
    {
        "material_name": "Brick Partition Plastered (100mm)",
        "unit_of_measurement": "sqft",
        "cost_inr": 62.0,
        "category": "wall",
    },
    # Flooring (8)
    {
        "material_name": "Vitrified Tiles (600x600mm)",
        "unit_of_measurement": "sqft",
        "cost_inr": 45.0,
        "category": "flooring",
    },
    {
        "material_name": "Ceramic Floor Tiles (300x300mm)",
        "unit_of_measurement": "sqft",
        "cost_inr": 35.0,
        "category": "flooring",
    },
    {
        "material_name": "Premium Vinyl Flooring (2mm)",
        "unit_of_measurement": "sqft",
        "cost_inr": 125.0,
        "category": "flooring",
    },
    {
        "material_name": "Engineered Wood Flooring",
        "unit_of_measurement": "sqft",
        "cost_inr": 260.0,
        "category": "flooring",
    },
    {
        "material_name": "Italian Marble Flooring",
        "unit_of_measurement": "sqft",
        "cost_inr": 420.0,
        "category": "flooring",
    },
    {
        "material_name": "Granite Flooring",
        "unit_of_measurement": "sqft",
        "cost_inr": 190.0,
        "category": "flooring",
    },
    {
        "material_name": "Anti-Skid Ceramic Tiles",
        "unit_of_measurement": "sqft",
        "cost_inr": 55.0,
        "category": "flooring",
    },
    {
        "material_name": "Epoxy Flooring (self-leveling)",
        "unit_of_measurement": "sqft",
        "cost_inr": 155.0,
        "category": "flooring",
    },
    # Ceiling (4)
    {
        "material_name": "Gypsum False Ceiling (plain)",
        "unit_of_measurement": "sqft",
        "cost_inr": 65.0,
        "category": "ceiling",
    },
    {
        "material_name": "Mineral Fiber Ceiling Tiles (600x600mm)",
        "unit_of_measurement": "sqft",
        "cost_inr": 85.0,
        "category": "ceiling",
    },
    {
        "material_name": "POP False Ceiling",
        "unit_of_measurement": "sqft",
        "cost_inr": 50.0,
        "category": "ceiling",
    },
    {
        "material_name": "Metal Grid Ceiling (exposed)",
        "unit_of_measurement": "sqft",
        "cost_inr": 110.0,
        "category": "ceiling",
    },
    # Door (4)
    {
        "material_name": "HDF Flush Door (35mm)",
        "unit_of_measurement": "piece",
        "cost_inr": 4800.0,
        "category": "door",
    },
    {
        "material_name": "Glass Swing Door (10mm tempered)",
        "unit_of_measurement": "piece",
        "cost_inr": 12500.0,
        "category": "door",
    },
    {
        "material_name": "Fire-Rated Door (30 min)",
        "unit_of_measurement": "piece",
        "cost_inr": 9500.0,
        "category": "door",
    },
    {
        "material_name": "Sliding Glass Door Panel",
        "unit_of_measurement": "piece",
        "cost_inr": 16000.0,
        "category": "door",
    },
    # Door hardware (3)
    {
        "material_name": "Aluminum Door Frame",
        "unit_of_measurement": "running_foot",
        "cost_inr": 195.0,
        "category": "door_hardware",
    },
    {
        "material_name": "Stainless Steel Handle Set",
        "unit_of_measurement": "piece",
        "cost_inr": 650.0,
        "category": "door_hardware",
    },
    {
        "material_name": "Hydraulic Door Closer",
        "unit_of_measurement": "piece",
        "cost_inr": 1200.0,
        "category": "door_hardware",
    },
    # Paint (4)
    {
        "material_name": "Interior Acrylic Emulsion (per coat)",
        "unit_of_measurement": "sqft",
        "cost_inr": 14.0,
        "category": "paint",
    },
    {
        "material_name": "Wall Primer (1 coat)",
        "unit_of_measurement": "sqft",
        "cost_inr": 8.0,
        "category": "paint",
    },
    {
        "material_name": "Texture Paint (roller finish)",
        "unit_of_measurement": "sqft",
        "cost_inr": 28.0,
        "category": "paint",
    },
    {
        "material_name": "Anti-Fungal Paint",
        "unit_of_measurement": "sqft",
        "cost_inr": 20.0,
        "category": "paint",
    },
    # Electrical (5)
    {
        "material_name": "LED Panel Light Point (with wiring)",
        "unit_of_measurement": "piece",
        "cost_inr": 850.0,
        "category": "electrical",
    },
    {
        "material_name": "Power Socket (5A modular)",
        "unit_of_measurement": "piece",
        "cost_inr": 380.0,
        "category": "electrical",
    },
    {
        "material_name": "Modular Switch Board (4-module)",
        "unit_of_measurement": "piece",
        "cost_inr": 480.0,
        "category": "electrical",
    },
    {
        "material_name": "Data/Network Point (CAT6)",
        "unit_of_measurement": "piece",
        "cost_inr": 1250.0,
        "category": "electrical",
    },
    {
        "material_name": "AC Point (with copper piping stub)",
        "unit_of_measurement": "piece",
        "cost_inr": 3800.0,
        "category": "electrical",
    },
    # Baseboard (2)
    {
        "material_name": "PVC Skirting (75mm)",
        "unit_of_measurement": "running_foot",
        "cost_inr": 28.0,
        "category": "baseboard",
    },
    {
        "material_name": "Wooden Skirting (75mm teak)",
        "unit_of_measurement": "running_foot",
        "cost_inr": 90.0,
        "category": "baseboard",
    },
    # Waterproofing (3)
    {
        "material_name": "Cementitious Waterproofing (2-coat)",
        "unit_of_measurement": "sqft",
        "cost_inr": 38.0,
        "category": "waterproofing",
    },
    {
        "material_name": "Liquid Membrane Waterproofing",
        "unit_of_measurement": "sqft",
        "cost_inr": 58.0,
        "category": "waterproofing",
    },
    {
        "material_name": "Waterproof Ceramic Wall Tiles",
        "unit_of_measurement": "sqft",
        "cost_inr": 65.0,
        "category": "waterproofing",
    },
    # Specialty (5)
    {
        "material_name": "Raised Access Flooring (steel pedestal)",
        "unit_of_measurement": "sqft",
        "cost_inr": 235.0,
        "category": "specialty",
    },
    {
        "material_name": "Kitchen Backsplash Tiles (ceramic)",
        "unit_of_measurement": "sqft",
        "cost_inr": 78.0,
        "category": "specialty",
    },
    {
        "material_name": "Acoustic Soundproofing Panel",
        "unit_of_measurement": "sqft",
        "cost_inr": 185.0,
        "category": "specialty",
    },
    {
        "material_name": "Anti-Static Vinyl Flooring",
        "unit_of_measurement": "sqft",
        "cost_inr": 165.0,
        "category": "specialty",
    },
    {
        "material_name": "Stainless Steel Backsplash",
        "unit_of_measurement": "sqft",
        "cost_inr": 260.0,
        "category": "specialty",
    },
]


def get_database_url() -> str:
    """Construct PostgreSQL connection URL from Supabase credentials."""
    # Supabase PostgreSQL connection format
    # postgresql://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres

    project_url = settings.SUPABASE_PROJECT_URL.strip()
    if not project_url:
        raise ValueError("SUPABASE_PROJECT_URL not set in .env")
    if not project_url.startswith("https://"):
        raise ValueError("SUPABASE_PROJECT_URL must start with https://")
    if ".supabase.co" not in project_url:
        raise ValueError("SUPABASE_PROJECT_URL must be a supabase.co domain")

    project_ref = (
        project_url.replace("https://", "")
        .replace(".supabase.co", "")
        .replace("/", "")
        .strip()
    )
    if not project_ref:
        raise ValueError("Could not extract project ref from SUPABASE_PROJECT_URL")

    password = settings.SUPABASE_PASSWORD

    if not password:
        raise ValueError("SUPABASE_PASSWORD not set in .env")

    return (
        f"postgresql://postgres:{password}@db.{project_ref}.supabase.co:5432/postgres"
    )


def create_tables(engine):
    """Create all tables defined in SQLModel."""
    print("📊 Creating database tables...")
    SQLModel.metadata.create_all(engine)
    print("✅ Tables created successfully")


def seed_materials(session: Session):
    """Seed materials_pricing table with default materials."""
    print("\n🏗️ Seeding materials pricing...")

    existing_materials = session.exec(select(MaterialPricing)).all()
    if existing_materials:
        for material in existing_materials:
            session.delete(material)
        session.commit()
        print(f"🔄 Cleared {len(existing_materials)} existing materials for re-seed")

    for material_data in DEFAULT_MATERIALS:
        material = MaterialPricing(**material_data)
        session.add(material)

    session.commit()
    print(f"✅ Seeded {len(DEFAULT_MATERIALS)} materials")

    seeded_materials = session.exec(select(MaterialPricing)).all()
    category_counts = Counter(material.category for material in seeded_materials)

    print("\n📦 Category breakdown:")
    for category, count in sorted(category_counts.items()):
        print(f"   • {category}: {count}")

    print("\n📋 Material catalog:")
    for material in seeded_materials:
        print(
            "   • "
            f"{material.material_name} [{material.category}]: "
            f"₹{material.cost_inr}/{material.unit_of_measurement}"
        )


def create_sample_project(session: Session):
    """Create a sample project with floorplan and BOM for testing."""
    print("\n📁 Creating sample project...")

    # Check if sample project already exists
    existing = session.exec(
        select(Project).where(Project.project_name == "Sample Office Fit-out")
    ).first()
    if existing:
        print("⚠️  Sample project already exists. Skipping.")
        return existing

    # Create project
    project = Project(
        project_name="Sample Office Fit-out",
        client_name="TechStart India Pvt Ltd",
        status="active",
    )
    session.add(project)
    session.commit()
    session.refresh(project)

    project_id = project.id
    if project_id is None:
        raise RuntimeError("Failed to generate project ID")

    print(f"✅ Created project: {project.project_name} (ID: {project_id})")

    # Create floorplan
    floorplan = Floorplan(
        project_id=project_id,
        pdf_storage_url="https://mfhglyvspxbmguilkdwx.supabase.co/storage/v1/object/public/floorplans/sample-office.pdf",
        raw_vector_data={
            "lines": 127,
            "page_dimensions": [612, 792],
            "extracted_at": datetime.utcnow().isoformat(),
            "wall_types": ["outer", "interior", "partition"],
            "rooms_detected": ["reception", "workspace", "meeting_room", "pantry"],
        },
        status="processed",
    )
    session.add(floorplan)
    session.commit()
    session.refresh(floorplan)

    floorplan_id = floorplan.id
    if floorplan_id is None:
        raise RuntimeError("Failed to generate floorplan ID")

    print(f"✅ Created floorplan (ID: {floorplan_id})")

    # Create BOM
    bom = GeneratedBOM(
        floorplan_id=floorplan_id,
        total_cost_inr=1250000.0,
        bom_data={
            "generated_at": datetime.utcnow().isoformat(),
            "line_items": [
                {
                    "material": "Standard Gypsum Drywall (12mm)",
                    "quantity": 450,
                    "unit": "sqft",
                    "rate": 45,
                    "amount": 20250,
                },
                {
                    "material": "Tempered Glass Partition (10mm)",
                    "quantity": 120,
                    "unit": "sqft",
                    "rate": 350,
                    "amount": 42000,
                },
                {
                    "material": "Vitrified Tiles (600x600mm)",
                    "quantity": 800,
                    "unit": "sqft",
                    "rate": 85,
                    "amount": 68000,
                },
                {
                    "material": "Premium Vinyl Flooring (2mm)",
                    "quantity": 600,
                    "unit": "sqft",
                    "rate": 120,
                    "amount": 72000,
                },
                {
                    "material": "Aluminum Door Frame",
                    "quantity": 80,
                    "unit": "running_foot",
                    "rate": 180,
                    "amount": 14400,
                },
                {
                    "material": "HDF Flush Door (35mm)",
                    "quantity": 8,
                    "unit": "piece",
                    "rate": 4500,
                    "amount": 36000,
                },
            ],
            "summary": {
                "total_area_sqft": 2000,
                "room_count": 4,
                "labor_estimate_inr": 250000,
            },
        },
    )
    session.add(bom)
    session.commit()
    print(f"✅ Created BOM (ID: {bom.id})")
    print(f"   Total Cost: ₹{bom.total_cost_inr:,.2f}")

    return project


def main():
    """Main setup function."""
    print("=" * 60)
    print("SUPABASE SCHEMA SETUP")
    print("=" * 60)

    try:
        # Get database URL
        database_url = get_database_url()
        print(f"\n🔗 Connecting to: {database_url[:50]}...")

        # Create engine
        engine = create_engine(database_url, echo=False)

        # Create tables
        create_tables(engine)

        # Seed data
        with Session(engine) as session:
            seed_materials(session)
            project = create_sample_project(session)

        print("\n" + "=" * 60)
        print("✅ SETUP COMPLETE")
        print("=" * 60)
        print("\nYour Supabase database is ready with:")
        print("  • 4 tables: projects, floorplans, materials_pricing, generated_boms")
        print(
            "  • 45 default materials across 10 categories with Indian market pricing"
        )
        print("  • 1 sample project with floorplan and BOM")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

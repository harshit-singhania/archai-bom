#!/usr/bin/env python3
"""
Setup Supabase schema and seed data.

This script:
1. Creates the database tables using SQLModel
2. Seeds materials_pricing with 10 basic materials
3. Creates sample project with floorplan and BOM

Usage:
    python scripts/setup_supabase_schema.py
"""

import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import SQLModel, create_engine, Session, select
from app.core.config import settings
from app.models.database import Project, Floorplan, MaterialPricing, GeneratedBOM


# Hardcoded materials for Indian market (MVP starter set)
DEFAULT_MATERIALS = [
    {"material_name": "Standard Gypsum Drywall (12mm)", "unit_of_measurement": "sqft", "cost_inr": 45.0},
    {"material_name": "Moisture-Resistant Drywall (12mm)", "unit_of_measurement": "sqft", "cost_inr": 65.0},
    {"material_name": "Tempered Glass Partition (10mm)", "unit_of_measurement": "sqft", "cost_inr": 350.0},
    {"material_name": "Laminated Glass Partition (12mm)", "unit_of_measurement": "sqft", "cost_inr": 450.0},
    {"material_name": "Vitrified Tiles (600x600mm)", "unit_of_measurement": "sqft", "cost_inr": 85.0},
    {"material_name": "Ceramic Wall Tiles (300x600mm)", "unit_of_measurement": "sqft", "cost_inr": 55.0},
    {"material_name": "Premium Vinyl Flooring (2mm)", "unit_of_measurement": "sqft", "cost_inr": 120.0},
    {"material_name": "Engineered Wood Flooring", "unit_of_measurement": "sqft", "cost_inr": 250.0},
    {"material_name": "Aluminum Door Frame", "unit_of_measurement": "running_foot", "cost_inr": 180.0},
    {"material_name": "HDF Flush Door (35mm)", "unit_of_measurement": "piece", "cost_inr": 4500.0},
]


def get_database_url() -> str:
    """Construct PostgreSQL connection URL from Supabase credentials."""
    # Supabase PostgreSQL connection format
    # postgresql://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres
    
    project_ref = settings.SUPABASE_PROJECT_URL.replace("https://", "").replace(".supabase.co", "")
    password = settings.SUPABASE_PASSWORD
    
    if not password:
        raise ValueError("SUPABASE_PASSWORD not set in .env")
    
    return f"postgresql://postgres:{password}@db.{project_ref}.supabase.co:5432/postgres"


def create_tables(engine):
    """Create all tables defined in SQLModel."""
    print("📊 Creating database tables...")
    SQLModel.metadata.create_all(engine)
    print("✅ Tables created successfully")


def seed_materials(session: Session):
    """Seed materials_pricing table with default materials."""
    print("\n🏗️ Seeding materials pricing...")
    
    # Check if materials already exist
    existing = session.exec(select(MaterialPricing)).first()
    if existing:
        print("⚠️  Materials already seeded. Skipping.")
        return
    
    for material_data in DEFAULT_MATERIALS:
        material = MaterialPricing(**material_data)
        session.add(material)
    
    session.commit()
    print(f"✅ Seeded {len(DEFAULT_MATERIALS)} materials")
    
    # Print summary
    for material in session.exec(select(MaterialPricing)):
        print(f"   • {material.material_name}: ₹{material.cost_inr}/{material.unit_of_measurement}")


def create_sample_project(session: Session):
    """Create a sample project with floorplan and BOM for testing."""
    print("\n📁 Creating sample project...")
    
    # Check if sample project already exists
    existing = session.exec(select(Project).where(Project.project_name == "Sample Office Fit-out")).first()
    if existing:
        print("⚠️  Sample project already exists. Skipping.")
        return existing
    
    # Create project
    project = Project(
        project_name="Sample Office Fit-out",
        client_name="TechStart India Pvt Ltd",
        status="active"
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    print(f"✅ Created project: {project.project_name} (ID: {project.id})")
    
    # Create floorplan
    floorplan = Floorplan(
        project_id=project.id,
        pdf_storage_url="https://mfhglyvspxbmguilkdwx.supabase.co/storage/v1/object/public/floorplans/sample-office.pdf",
        raw_vector_data={
            "lines": 127,
            "page_dimensions": [612, 792],
            "extracted_at": datetime.utcnow().isoformat(),
            "wall_types": ["outer", "interior", "partition"],
            "rooms_detected": ["reception", "workspace", "meeting_room", "pantry"]
        },
        status="processed"
    )
    session.add(floorplan)
    session.commit()
    session.refresh(floorplan)
    print(f"✅ Created floorplan (ID: {floorplan.id})")
    
    # Create BOM
    bom = GeneratedBOM(
        floorplan_id=floorplan.id,
        total_cost_inr=1250000.0,
        bom_data={
            "generated_at": datetime.utcnow().isoformat(),
            "line_items": [
                {"material": "Standard Gypsum Drywall (12mm)", "quantity": 450, "unit": "sqft", "rate": 45, "amount": 20250},
                {"material": "Tempered Glass Partition (10mm)", "quantity": 120, "unit": "sqft", "rate": 350, "amount": 42000},
                {"material": "Vitrified Tiles (600x600mm)", "quantity": 800, "unit": "sqft", "rate": 85, "amount": 68000},
                {"material": "Premium Vinyl Flooring (2mm)", "quantity": 600, "unit": "sqft", "rate": 120, "amount": 72000},
                {"material": "Aluminum Door Frame", "quantity": 80, "unit": "running_foot", "rate": 180, "amount": 14400},
                {"material": "HDF Flush Door (35mm)", "quantity": 8, "unit": "piece", "rate": 4500, "amount": 36000},
            ],
            "summary": {
                "total_area_sqft": 2000,
                "room_count": 4,
                "labor_estimate_inr": 250000
            }
        }
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
        print("  • 10 default materials with Indian market pricing")
        print("  • 1 sample project with floorplan and BOM")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

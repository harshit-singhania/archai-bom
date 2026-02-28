import pytest
from unittest.mock import patch, MagicMock
from sqlmodel import Session

from app.core import database as db_module
from app.models.database import Project, Floorplan, GeneratedBOM

# test_db fixture is provided by tests/conftest.py (Supabase-backed)


def test_session_factory_uses_test_database(test_db, monkeypatch):
    """Test that session factory uses the configured database."""
    with db_module.get_session() as session:
        # Should be able to create a project
        project = Project(project_name="Test Project", client_name="Test Client")
        session.add(project)
        session.commit()
        session.refresh(project)

        assert project.id is not None
        assert project.project_name == "Test Project"


def test_get_database_url_from_settings(monkeypatch):
    """Test that database URL is constructed from settings."""
    # Test with explicit DATABASE_URL
    monkeypatch.setattr(
        db_module.settings, "DATABASE_URL", "postgresql://user:pass@localhost/db"
    )
    monkeypatch.setattr(db_module.settings, "SUPABASE_PROJECT_URL", "")
    monkeypatch.setattr(db_module.settings, "SUPABASE_PASSWORD", "")

    url = db_module.get_database_url()
    assert url == "postgresql://user:pass@localhost/db"


def test_get_database_url_from_supabase(monkeypatch):
    """Test that database URL is constructed from Supabase credentials."""
    monkeypatch.setattr(db_module.settings, "DATABASE_URL", "")
    monkeypatch.setattr(
        db_module.settings, "SUPABASE_PROJECT_URL", "https://abc123.supabase.co"
    )
    monkeypatch.setattr(db_module.settings, "SUPABASE_PASSWORD", "test-password")

    url = db_module.get_database_url()
    assert (
        "postgresql://postgres:test-password@db.abc123.supabase.co:5432/postgres" == url
    )


def test_get_database_url_raises_on_missing_config(monkeypatch):
    """Test that get_database_url raises on missing configuration."""
    monkeypatch.setattr(db_module.settings, "DATABASE_URL", "")
    monkeypatch.setattr(db_module.settings, "SUPABASE_PROJECT_URL", "")
    monkeypatch.setattr(db_module.settings, "SUPABASE_PASSWORD", "")

    with pytest.raises(ValueError, match="Database configuration incomplete"):
        db_module.get_database_url()


def test_reset_engine():
    """Test that reset_engine clears the cached engine."""
    # Set some state
    db_module._engine = MagicMock()
    db_module._session_maker = MagicMock()

    # Reset
    db_module.reset_engine()

    # Should be None
    assert db_module._engine is None
    assert db_module._session_maker is None


# =============================================================================
# REPOSITORY TESTS
# =============================================================================

from app.repositories.project_repository import (
    create_project,
    get_project_by_id,
    list_projects,
    update_project_status,
)
from app.repositories.floorplan_repository import (
    create_floorplan,
    get_floorplan_by_id,
    list_floorplans_by_project,
    update_floorplan_status,
    update_floorplan_vector_data,
)
from app.repositories.bom_repository import (
    create_bom,
    get_bom_by_id,
    get_bom_by_floorplan,
    update_bom_data,
)


class TestProjectRepository:
    """Tests for project repository."""

    def test_create_project(self, test_db):
        project_id = create_project(
            project_name="Test Project", client_name="Test Client"
        )
        assert project_id is not None

        # Verify by fetching
        fetched = get_project_by_id(project_id)
        assert fetched is not None
        assert fetched["project_name"] == "Test Project"
        assert fetched["client_name"] == "Test Client"
        assert fetched["status"] == "active"

    def test_get_project_by_id(self, test_db):
        created_id = create_project(
            project_name="Test Project", client_name="Test Client"
        )
        fetched = get_project_by_id(created_id)

        assert fetched is not None
        assert fetched["id"] == created_id
        assert fetched["project_name"] == "Test Project"

    def test_get_project_by_id_not_found(self, test_db):
        fetched = get_project_by_id(99999)
        assert fetched is None

    def test_list_projects(self, test_db):
        create_project(project_name="Project 1", client_name="Client 1")
        create_project(project_name="Project 2", client_name="Client 2")

        projects = list_projects()
        assert len(projects) >= 2

    def test_list_projects_by_status(self, test_db):
        create_project(project_name="Active Project", client_name="Client")

        active_projects = list_projects(status="active")
        assert len(active_projects) >= 1

        archived_projects = list_projects(status="archived")
        # May be empty, but should not error
        assert isinstance(archived_projects, list)

    def test_update_project_status(self, test_db):
        project_id = create_project(
            project_name="Test Project", client_name="Test Client"
        )
        updated = update_project_status(project_id, "completed")

        assert updated is True

        # Verify persistence
        fetched = get_project_by_id(project_id)
        assert fetched["status"] == "completed"


class TestFloorplanRepository:
    """Tests for floorplan repository."""

    def test_create_floorplan(self, test_db):
        # First create a project
        project_id = create_project(
            project_name="Test Project", client_name="Test Client"
        )

        floorplan_id = create_floorplan(
            project_id=project_id,
            pdf_storage_url="https://example.com/test.pdf",
            raw_vector_data={"lines": 10},
            status="uploaded",
        )

        assert floorplan_id is not None

        # Verify by fetching
        fetched = get_floorplan_by_id(floorplan_id)
        assert fetched["project_id"] == project_id
        assert fetched["status"] == "uploaded"

    def test_get_floorplan_by_id(self, test_db):
        project_id = create_project(
            project_name="Test Project", client_name="Test Client"
        )
        created_id = create_floorplan(
            project_id=project_id, pdf_storage_url="https://example.com/test.pdf"
        )

        fetched = get_floorplan_by_id(created_id)
        assert fetched is not None
        assert fetched["id"] == created_id

    def test_list_floorplans_by_project(self, test_db):
        project_id = create_project(
            project_name="Test Project", client_name="Test Client"
        )
        create_floorplan(
            project_id=project_id, pdf_storage_url="https://example.com/1.pdf"
        )
        create_floorplan(
            project_id=project_id, pdf_storage_url="https://example.com/2.pdf"
        )

        floorplans = list_floorplans_by_project(project_id)
        assert len(floorplans) == 2

    def test_update_floorplan_status(self, test_db):
        project_id = create_project(
            project_name="Test Project", client_name="Test Client"
        )
        floorplan_id = create_floorplan(
            project_id=project_id,
            pdf_storage_url="https://example.com/test.pdf",
            status="uploaded",
        )

        updated = update_floorplan_status(floorplan_id, "processed")
        assert updated is True

        # Verify by fetching
        fetched = get_floorplan_by_id(floorplan_id)
        assert fetched["status"] == "processed"

    def test_update_floorplan_vector_data(self, test_db):
        project_id = create_project(
            project_name="Test Project", client_name="Test Client"
        )
        floorplan_id = create_floorplan(
            project_id=project_id,
            pdf_storage_url="https://example.com/test.pdf",
            raw_vector_data={"initial": "data"},
        )

        updated = update_floorplan_vector_data(floorplan_id, {"extracted": "walls"})
        assert updated is True

        # Verify by fetching
        fetched = get_floorplan_by_id(floorplan_id)
        assert fetched["raw_vector_data"] == {"extracted": "walls"}


class TestBOMRepository:
    """Tests for BOM repository."""

    def test_create_bom(self, test_db):
        project_id = create_project(
            project_name="Test Project", client_name="Test Client"
        )
        floorplan_id = create_floorplan(
            project_id=project_id, pdf_storage_url="https://example.com/test.pdf"
        )

        bom_id = create_bom(
            floorplan_id=floorplan_id,
            total_cost_inr=100000.0,
            bom_data={"items": [{"name": "Drywall", "cost": 50000}]},
        )

        assert bom_id is not None

        # Verify by fetching
        fetched = get_bom_by_id(bom_id)
        assert fetched["floorplan_id"] == floorplan_id
        assert fetched["total_cost_inr"] == 100000.0

    def test_get_bom_by_id(self, test_db):
        project_id = create_project(
            project_name="Test Project", client_name="Test Client"
        )
        floorplan_id = create_floorplan(
            project_id=project_id, pdf_storage_url="https://example.com/test.pdf"
        )
        created_id = create_bom(floorplan_id=floorplan_id, total_cost_inr=100000.0)

        fetched = get_bom_by_id(created_id)
        assert fetched is not None
        assert fetched["id"] == created_id

    def test_get_bom_by_floorplan(self, test_db):
        project_id = create_project(
            project_name="Test Project", client_name="Test Client"
        )
        floorplan_id = create_floorplan(
            project_id=project_id, pdf_storage_url="https://example.com/test.pdf"
        )
        created_id = create_bom(floorplan_id=floorplan_id, total_cost_inr=100000.0)

        fetched = get_bom_by_floorplan(floorplan_id)
        assert fetched is not None
        assert fetched["id"] == created_id

    def test_update_bom_data(self, test_db):
        project_id = create_project(
            project_name="Test Project", client_name="Test Client"
        )
        floorplan_id = create_floorplan(
            project_id=project_id, pdf_storage_url="https://example.com/test.pdf"
        )
        bom_id = create_bom(
            floorplan_id=floorplan_id,
            total_cost_inr=100000.0,
            bom_data={"initial": "data"},
        )

        updated = update_bom_data(
            bom_id, total_cost_inr=150000.0, bom_data={"updated": "data"}
        )
        assert updated is True

        # Verify by fetching
        fetched = get_bom_by_id(bom_id)
        assert fetched["total_cost_inr"] == 150000.0
        assert fetched["bom_data"] == {"updated": "data"}

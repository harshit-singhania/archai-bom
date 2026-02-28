"""Project repository for database operations."""

from typing import Optional, List
from sqlmodel import select

from app.core.database import get_session
from app.models.database import Project


def create_project(project_name: str, client_name: str, status: str = "active") -> int:
    """Create a new project.

    Args:
        project_name: Name of the project
        client_name: Name of the client
        status: Project status (active, completed, archived)

    Returns:
        Created Project ID
    """
    with get_session() as session:
        project = Project(
            project_name=project_name, client_name=client_name, status=status
        )
        session.add(project)
        session.commit()
        session.refresh(project)
        return project.id


def get_project_by_id(project_id: int) -> Optional[dict]:
    """Get a project by ID.

    Args:
        project_id: The project ID

    Returns:
        Project dict or None if not found
    """
    with get_session() as session:
        project = session.get(Project, project_id)
        if project:
            return {
                "id": project.id,
                "project_name": project.project_name,
                "client_name": project.client_name,
                "status": project.status,
                "created_at": project.created_at,
            }
        return None


def list_projects(status: Optional[str] = None) -> List[dict]:
    """List all projects, optionally filtered by status.

    Args:
        status: Optional status filter

    Returns:
        List of Project dicts
    """
    with get_session() as session:
        query = select(Project)
        if status:
            query = query.where(Project.status == status)
        projects = session.exec(query).all()
        return [
            {
                "id": p.id,
                "project_name": p.project_name,
                "client_name": p.client_name,
                "status": p.status,
                "created_at": p.created_at,
            }
            for p in projects
        ]


def update_project_status(project_id: int, status: str) -> bool:
    """Update a project's status.

    Args:
        project_id: The project ID
        status: New status value

    Returns:
        True if updated, False if not found
    """
    with get_session() as session:
        project = session.get(Project, project_id)
        if project:
            project.status = status
            session.add(project)
            session.commit()
            return True
        return False

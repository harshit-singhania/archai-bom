"""Layout generation service using Google Gemini."""

import json
from typing import Any

from google import genai
from google.genai import types
from pydantic import ValidationError

from app.core.config import settings
from app.models.layout import GeneratedLayout
from app.models.spatial import SpatialGraph


def _mm_per_pdf_point(scale_factor: float | None) -> float:
    """Convert one PDF point to millimeters."""

    if scale_factor is None or scale_factor <= 0:
        return 1.0

    # Phase-1 scale_factor can be missing or effectively unknown in practice.
    # Values close to 1.0 are treated as uncalibrated and we keep 1 pt = 1 mm.
    if scale_factor <= 2.0:
        return 1.0

    return 304.8 / scale_factor


def _to_perimeter_walls_mm(
    spatial_graph: SpatialGraph, mm_per_point: float
) -> list[dict[str, float | str]]:
    """Convert perimeter walls from PDF points to mm."""

    perimeter_walls: list[dict[str, float | str]] = []
    for index, wall in enumerate(spatial_graph.walls, start=1):
        perimeter_walls.append(
            {
                "id": f"perimeter_{index}",
                "x1": wall.x1 * mm_per_point,
                "y1": wall.y1 * mm_per_point,
                "x2": wall.x2 * mm_per_point,
                "y2": wall.y2 * mm_per_point,
                "thickness_mm": wall.thickness * mm_per_point,
            }
        )
    return perimeter_walls


def _build_prompt(
    spatial_graph: SpatialGraph,
    prompt: str,
    perimeter_walls: list[dict[str, float | str]],
    page_dimensions_mm: tuple[float, float],
) -> str:
    """Construct generation prompt with all required context and schema."""

    room_context: list[dict[str, Any]] = []
    for room in spatial_graph.rooms:
        room_context.append(
            {
                "name": room.name,
                "area_sq_pts": room.area_sq_pts,
                "area_sq_ft": room.area_sq_ft,
                "boundary_wall_indices": room.boundary_walls,
            }
        )

    bbox = {
        "min_x": 0.0,
        "min_y": 0.0,
        "max_x": page_dimensions_mm[0],
        "max_y": page_dimensions_mm[1],
    }
    if perimeter_walls:
        all_x = [
            coord for wall in perimeter_walls for coord in (wall["x1"], wall["x2"])
        ]
        all_y = [
            coord for wall in perimeter_walls for coord in (wall["y1"], wall["y2"])
        ]
        bbox = {
            "min_x": min(all_x),
            "min_y": min(all_y),
            "max_x": max(all_x),
            "max_y": max(all_y),
        }

    schema = GeneratedLayout.model_json_schema()

    return (
        "You are an expert interior layout planner.\n"
        "Generate a complete layout JSON that conforms exactly to the provided schema.\n\n"
        "Perimeter walls in millimeters:\n"
        f"{json.dumps(perimeter_walls, indent=2)}\n\n"
        "Perimeter bounding box in millimeters:\n"
        f"{json.dumps(bbox, indent=2)}\n\n"
        "Page dimensions in millimeters:\n"
        f"{json.dumps({'width_mm': page_dimensions_mm[0], 'height_mm': page_dimensions_mm[1]}, indent=2)}\n\n"
        "Extracted room hints from the spatial graph:\n"
        f"{json.dumps(room_context, indent=2)}\n\n"
        "User description:\n"
        f"{prompt}\n\n"
        "Generate interior walls, doors, and fixtures that subdivide the perimeter into the described rooms. "
        "All coordinates must be in millimeters.\n"
        "Return only valid JSON.\n\n"
        "JSON schema:\n"
        f"{json.dumps(schema, indent=2)}"
    )


def _parse_layout_response(response: Any) -> GeneratedLayout:
    """Parse Gemini response into GeneratedLayout model."""

    raw_text = getattr(response, "text", "")

    if getattr(response, "parsed", None) is not None:
        parsed = response.parsed
        try:
            return GeneratedLayout.model_validate(parsed)
        except ValidationError as exc:
            raise ValueError(
                f"Gemini returned invalid GeneratedLayout payload: {parsed}"
            ) from exc

    if raw_text:
        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Gemini returned non-JSON response: {raw_text}") from exc

        try:
            return GeneratedLayout.model_validate(payload)
        except ValidationError as exc:
            raise ValueError(
                f"Gemini returned invalid GeneratedLayout payload: {payload}"
            ) from exc

    raise ValueError(f"Gemini response missing parsed/text payload: {response}")


def generate_layout(spatial_graph: SpatialGraph, prompt: str) -> GeneratedLayout:
    """Generate an interior layout from a spatial graph and natural language prompt."""

    if not settings.GOOGLE_API_KEY:
        raise RuntimeError("GOOGLE_API_KEY is not set; layout generation cannot run.")

    mm_per_point = _mm_per_pdf_point(spatial_graph.scale_factor)
    perimeter_walls = _to_perimeter_walls_mm(spatial_graph, mm_per_point)
    page_dimensions_mm = (
        spatial_graph.page_dimensions[0] * mm_per_point,
        spatial_graph.page_dimensions[1] * mm_per_point,
    )
    generation_prompt = _build_prompt(
        spatial_graph=spatial_graph,
        prompt=prompt,
        perimeter_walls=perimeter_walls,
        page_dimensions_mm=page_dimensions_mm,
    )

    client = genai.Client(api_key=settings.GOOGLE_API_KEY)
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[generation_prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_json_schema=GeneratedLayout.model_json_schema(),
                temperature=0.2,
            ),
        )
    except Exception as exc:
        raise RuntimeError(f"Gemini layout generation failed: {exc}") from exc

    return _parse_layout_response(response)

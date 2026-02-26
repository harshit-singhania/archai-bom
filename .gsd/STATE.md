# STATE.md — Session Memory

> **Purpose**: Persist project state across sessions. Update after each wave or significant work block.

---

## Current Position

**Phase:** 3 — Deterministic Calculator + Async Pipeline
**Status:** Planning complete — ready for execution
**Active Task:** None — awaiting `/execute 3`
**Last Action:** Committed Phase 2 changes and pushed to GitHub (harshit-singhania/achai-bom) — 2026-02-26

---

## Key Decisions Made

- MVP scope: All 4 modules (not production-hardened) — ADR-001
- No AI in math layer — ADR-002
- Stack: Option A — Python/Flask + Supabase + SQLModel + React SPA
- PDF ingestion: PyMuPDF vector extraction + Gemini raster extraction + Google Gemini for semantics
- Raster PDF support: Gemini 2.5 Flash processes PNG at 2x scale, returns pixel coordinates converted to PDF points
- Spatial generation: Google Gemini + JSON DSL + Constraint Checker
- Database: Supabase PostgreSQL with SQLModel ORM
- Async queue: Celery + Redis (selected over RQ and RabbitMQ — see Phase 3 RESEARCH.md)
- BOM pricing: Hardcoded CPWD rates v1, API v2 (future)
- Excel export: openpyxl
- Default ceiling height: 10ft (3048mm), configurable per-project

---

## Phase 1 — COMPLETE

| Plan | Name | Wave | Status |
|------|------|------|--------|
| 1.1 | Project Scaffold & PyMuPDF Vector Extraction | 1 | ✅ COMPLETE |
| 1.2 | Layer Filtering & Wall Detection | 2 | ✅ COMPLETE |
| 1.2b | Raster PDF Wall Extraction (Gemini) | 2 | ✅ COMPLETE |
| 1.3 | Semantic Extraction & Spatial Graph Assembly | 3 | ✅ COMPLETE |

---

## Phase 2 — COMPLETE

| Plan | Name | Wave | Status |
|------|------|------|--------|
| 2.1 | Layout DSL Schema & Gemini Generation Service | 1 | ✅ COMPLETE |
| 2.2 | Constraint Validation & Grid Snapping | 2 | ✅ COMPLETE |
| 2.3 | Self-Correcting Generation Loop & API Integration | 3 | ✅ COMPLETE |

---

## Phase 3 — PLANNED

| Plan | Name | Wave | Status |
|------|------|------|--------|
| 3.1 | BOM Schema & India-Market Material Catalog | 1 | ⏳ Pending |
| 3.2 | Geometry-to-Quantity Rules Engine | 1 | ⏳ Pending |
| 3.3 | BOM Assembly, Pricing & XLSX Export | 2 | ⏳ Pending |
| 3.4 | Async Job Queue (Celery + Redis) | 2 | ⏳ Pending |
| 3.5 | End-to-End Pipeline Wiring & Integration Tests | 3 | ⏳ Pending |

**Wave dependency structure:**

- Wave 1 (parallel): Plans 3.1 + 3.2 — schemas and calculators
- Wave 2 (parallel): Plans 3.3 + 3.4 — assembly/export + async infra
- Wave 3: Plan 3.5 — wiring everything together

---

## Blockers

None — ready to execute Phase 3

---

## Next Steps

1. `/execute 3` — Execute Phase 3 plans (wave 1 first)

---

## Wave Summaries

### Phase 1 Waves (COMPLETE)

- Wave 1: Project scaffold, PyMuPDF extraction, database schema
- Wave 2: Wall detection, ingestion pipeline, raster PDF support
- Wave 3: Semantic extraction, spatial graph assembly

### Phase 2 Waves (COMPLETE)

- Wave 1: Layout DSL schema, Gemini generation service
- Wave 2: Constraint validation (Shapely), grid snapping (50mm)
- Wave 3: Self-correcting generation loop, parallel candidates, API integration

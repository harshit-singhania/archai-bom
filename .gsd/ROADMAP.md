---
milestone: ArchAI MVP v1.0
version: 0.1.0
updated: 2026-02-26
---

# ROADMAP.md

> **Current Phase:** 3 — Deterministic Calculator + Async Pipeline
> **Status:** planned — ready for execution

## Must-Haves (from SPEC)

- [ ] PDF ingestion extracts room boundaries and square footage from A-series drawings
- [ ] Natural language prompt populates spatial layout with appropriate geometry
- [ ] Deterministic calculator outputs priced BOM from geometry (no AI in math layer)
- [ ] Dual-pane dashboard delivers end-to-end workflow from upload to BOM export
- [ ] Correction capture logs contractor deltas for dataset building

---

## Phases

### Phase 1: Vision & Ingestion Engine
**Status:** ✅ Complete
**Objective:** Parse CAD-exported and scanned 2D floorplan PDFs into a structured spatial graph via PyMuPDF vector extraction + Gemini raster fallback + Gemini semantic labeling

**Plans:**
- [x] Plan 1.1: Project Scaffold & PyMuPDF Vector Extraction (wave 1)
- [x] Plan 1.2: Layer Filtering & Wall Detection (wave 2)
- [x] Plan 1.2b: Raster PDF Wall Extraction via Gemini (wave 2)
- [x] Plan 1.3: Semantic Extraction & Spatial Graph Assembly (wave 3)

---

### Phase 2: Spatial Generation Model
**Status:** ✅ Complete
**Objective:** Accept spatial graph + natural language prompt, generate optimized 2D layout with walls, desks, fixtures, and room-appropriate geometry
**Depends on:** Phase 1

**Plans:**
- [x] Plan 2.1: Layout DSL Schema & Gemini Generation Service (wave 1)
- [x] Plan 2.2: Constraint Validation & Grid Snapping (wave 2)
- [x] Plan 2.3: Self-Correcting Generation Loop & API Integration (wave 3)

---

### Phase 3: Deterministic Calculator + Async Pipeline
**Status:** 🔄 Planned — ready for execution
**Objective:** Convert generated geometry into a priced BOM spreadsheet using a strict rules engine (no AI in math layer), and add Celery + Redis async job queue for all long-running operations
**Depends on:** Phase 2

**Plans:**
- [ ] Plan 3.1: BOM Schema & India-Market Material Catalog (wave 1)
- [ ] Plan 3.2: Geometry-to-Quantity Rules Engine (wave 1)
- [ ] Plan 3.3: BOM Assembly, Pricing & XLSX Export (wave 2)
- [ ] Plan 3.4: Async Job Queue Infrastructure — Celery + Redis (wave 2)
- [ ] Plan 3.5: End-to-End Pipeline Wiring & Integration Tests (wave 3)

---

### Phase 4: Client Dashboard + Integration
**Status:** ⬜ Not Started
**Objective:** Dual-pane web application — PDF upload on left, 2D layout visualization + live BOM spreadsheet on right, with correction capture
**Depends on:** Phase 2, Phase 3

**Plans:**
- [ ] Plan 4.1: Select and scaffold frontend stack (post-research decision)
- [ ] Plan 4.2: Build PDF upload and ingestion trigger flow
- [ ] Plan 4.3: Build 2D layout visualization pane
- [ ] Plan 4.4: Build live BOM spreadsheet with inline editing
- [ ] Plan 4.5: Build correction capture — log delta between generated and submitted BOM
- [ ] Plan 4.6: End-to-end integration test + pilot contractor onboarding

---

## Progress Summary

| Phase | Status | Plans | Complete |
|-------|--------|-------|----------|
| 1 | ✅ | 4/4 | Done |
| 2 | ✅ | 3/3 | Done |
| 3 | 🔄 | 0/5 | Planned |
| 4 | ⬜ | 0/6 | — |

---

## Timeline

| Phase | Started | Completed | Duration |
|-------|---------|-----------|----------|
| 1 | 2026-02-25 | 2026-02-26 | 2 days |
| 2 | 2026-02-26 | 2026-02-26 | 1 day |
| 3 | — | — | — |
| 4 | — | — | — |

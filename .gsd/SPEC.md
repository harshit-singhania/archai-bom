# SPEC.md — Project Specification

> **Status**: `FINALIZED`

## Vision

ArchAI is an autonomous AI pipeline that converts 2D floorplan PDFs into priced Bills of Materials for commercial interior contractors. It compresses 3 weeks of manual CAD estimating into a 3-minute API call, targeting Chief Estimators in India's commercial interior fit-out market — where contractors currently spend 2–5% of revenue on estimation that loses 80% of bids due to human bottlenecks.

## Goals

1. **PDF Ingestion** — Extract room boundaries, dimensions, load-bearing elements, and scale from unstructured architectural drawings into a structured spatial graph
2. **Spatial Layout Generation** — Populate the spatial graph with walls, fixtures, and elements from a natural language prompt, understanding room-type geometry requirements
3. **Deterministic BOM Generation** — Apply localized construction math rules to generated geometry, producing a priced BOM spreadsheet without AI hallucination in the math layer
4. **Client Dashboard** — Deliver a dual-pane web UI for PDF upload, 2D layout visualization, and live BOM editing with change-capture for model improvement

## Non-Goals (Out of Scope for v1)

- MEP (mechanical, electrical, plumbing) system calculations
- Structural engineering and load calculations
- 3D rendering or BIM (Building Information Modeling) integration
- Multi-tenant SaaS features, team collaboration, or user management
- International markets outside India (pricing, codes, and regulations)
- Real-time pricing API integrations (v1 uses hardcoded local market rates)
- Automated permitting or code compliance checking
- Procurement or vendor management

## Users

**Primary: Chief Estimator** at commercial interior fit-out contractors in India. Responsible for bidding on office, dental clinic, retail, and hospitality interior projects. Currently spends 2–5% of company revenue on manual estimation using AutoCAD/Revit + spreadsheets. Loses ~80% of bids due to the time it takes to produce estimates.

**Secondary: Junior Architect** who currently performs the manual CAD tracing and spreadsheet work. Will become a reviewer and override operator rather than a generator.

## Constraints

- **Stack: Option A — The AI/Python Path** — Full Python-native stack for velocity and ecosystem:
  - **Backend**: Python/Flask — lightweight, flexible, extensive ecosystem for ML/CV (PyMuPDF, Google Generative AI)
  - **Database**: Supabase (PostgreSQL) — managed Postgres with auth, storage, and real-time features
  - **ORM**: SQLModel — combines Pydantic validation with SQLAlchemy ORM, keeping everything in one language
  - **AI**: Google Generative AI (Gemini) — multimodal capabilities for floorplan analysis
  - **Frontend**: React SPA (react-pdf + ag-grid-react) — See `.gsd/RESEARCH.md` for full rationale
  - **Rationale**: Avoids language context-switching, eliminates microservice overhead, leverages India's strong Python talent market, simpler deployment with Flask
- **No hallucination in BOM** — Generative AI must be architecturally firewalled from the deterministic calculator; the math engine takes geometry as input, not AI prose
- **India-market pricing** — Material rates must reflect local sourcing; not global commodity prices
- **MVP must be pilot-ready** — Output quality must be sufficient for a real contractor to stake a live bid on it

## Success Criteria

- [ ] System produces end-to-end output (PDF → BOM) for a clean A-series floorplan
- [ ] One real contractor uses the MVP on a live bid
- [ ] Contractor reports measurable time saving vs. manual estimation
- [ ] BOM output requires <10% manual correction by the contractor
- [ ] System captures contractor corrections as training delta (feedback loop initialized)

## User Stories

### As a Chief Estimator
- I want to upload a blank floorplan PDF and describe the space in plain language
- So that I receive a complete, priced BOM in minutes instead of weeks

### As a Chief Estimator
- I want to review and adjust the generated BOM line items
- So that I can apply my local knowledge and submit a competitive, accurate bid

### As a Junior Architect
- I want to see the AI-generated 2D layout before the BOM is computed
- So that I can catch spatial errors before they propagate to material quantities

## Technical Requirements

| Requirement | Priority | Notes |
|-------------|----------|-------|
| PDF ingestion handles A1/A2/A3 formats | Must-have | Standard Indian architectural drawing formats |
| BOM math is rule-based, not LLM-generated | Must-have | Deterministic, auditable, legally defensible |
| Dashboard loads generated layout in <30s | Should-have | UX threshold for pilot usability |
| BOM export to .xlsx | Must-have | Estimators work in Excel |
| Correction capture persists to dataset | Should-have | Core moat mechanism |
| Supports natural language room descriptions | Must-have | "6 operatory dental clinic", "60-seat boardroom" |
| PDF ingestion via vector extraction (PyMuPDF) | Must-have | Clean CAD exports with PyMuPDF vector parsing |
| PDF ingestion via raster extraction (Gemini Vision) | Must-have | Scanned/image PDFs processed via Gemini 2.5 Flash |
| Spatial generation via Claude + JSON DSL | Must-have | LangGraph constraint checker with max 3 iterations |
| Coordinates snap to 50mm construction grid | Must-have | Post-processing before constraint validation |

---

*Last updated: 2026-02-26*

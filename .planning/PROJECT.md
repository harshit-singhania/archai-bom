# ArchAI BOM — Project

## Core Value

**Compress 3 weeks of manual construction estimating into a 3-minute API call** by converting 2D floorplan PDFs into priced Bills of Materials for Indian commercial interior contractors.

## Vision

An autonomous AI pipeline that a contractor uploads a blank floorplan PDF to, describes the space, and receives back a fully priced BOM with material quantities, rates, and totals — ready to submit as a bid.

## Target User

**Chief Estimator** at an Indian commercial interior fit-out contractor. Manages 5-15 active bids. Currently spends 2-3 weeks per estimate using CAD + spreadsheets. Loses 80% of bids because they're too slow to respond.

## Success Criteria (MVP)

The MVP is successful when: **a contractor can upload a floorplan PDF, describe the space, and receive a priced BOM they would use to prepare a real bid — delivered through a web interface they can operate without a walkthrough.**

Concretely:
1. PDF upload → layout generation → priced BOM in <3 minutes
2. Visual layout rendering on screen (2D, rooms/walls/doors/fixtures)
3. BOM table with real Indian market pricing, editable inline
4. Export to Excel/PDF for client handoff
5. Self-serve usage (no developer in the room)

## Constraints

- **Timeline:** YC S26 applications ~mid-April 2026. Must be demo-ready by then.
- **Solo developer + Claude:** No team. Ship fast, cut scope ruthlessly.
- **No AI in the math layer:** BOM calculation is deterministic rules, not LLM generation. Construction math cannot hallucinate.
- **Indian market first:** All pricing, materials, units in Indian context (₹, sqft, mm).

## What's Built (Phase 1 — Concerns Remediation, Complete)

- PDF ingestion → wall/room detection (vector + raster Gemini fallback)
- Gemini-powered layout generation with constraint validation, retry, adaptive fanout
- Grid snapping, STRtree spatial indexing
- Supabase persistence (projects, floorplans, BOMs, async jobs)
- Async job queue (Redis/RQ) — non-blocking 202 API
- Security layer (API key auth, CORS, rate limiting, payload guards)
- Deterministic dependency management (pip-tools lockfile)
- 2100+ tests passing against real Supabase

## What's NOT Built (MVP Gaps)

- BOM calculator (geometry → material quantities × prices)
- Materials pricing engine (table exists, nothing consumes it)
- Frontend (no UI at all)
- Export (no PDF/Excel download)
- End-to-end connected flow

## Out of Scope (MVP)

- Multi-tenancy / user accounts / billing
- 3D extrusion
- Mobile responsive design
- CI/CD pipeline
- Comprehensive edge-case handling
- Real-time collaboration
- Version history / undo

## Key Decisions

| # | Decision | Rationale | Date |
|---|----------|-----------|------|
| 1 | React SPA (Vite + TypeScript) for frontend | Modern, fast, solo-dev friendly | 2026-02-27 |
| 2 | Seed ~40-50 materials at Indian market rates | Enough for convincing demo, client adds own later | 2026-02-27 |
| 3 | Deterministic BOM calculator (zero AI) | Construction math cannot hallucinate | 2026-02-27 |
| 4 | No auth in frontend for MVP | Demo-only, API key hardcoded | 2026-02-27 |
| 5 | SQLite test fixtures replaced with real Supabase | Production parity in tests | 2026-02-27 |

---
*Updated: 2026-02-27*

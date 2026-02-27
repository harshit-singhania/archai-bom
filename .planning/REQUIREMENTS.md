# Requirements: ArchAI BOM MVP

## v1 Requirements (Must Ship)

### BOM Calculator (BOM-)

- **BOM-01**: System converts generated layout geometry (walls, rooms, doors, fixtures) into material quantity takeoffs using deterministic construction rules
- **BOM-02**: Materials pricing database seeded with ~40-50 Indian market items at realistic ₹ rates across categories (drywall, glass, flooring, doors, ceiling, paint, electrical)
- **BOM-03**: BOM line items include material name, quantity, unit, rate (₹), and amount (₹) with a grand total
- **BOM-04**: Room-type-aware rules apply (bathroom → waterproofing, server room → raised flooring, kitchen → backsplash, etc.)
- **BOM-05**: Generate endpoint returns a fully priced BOM alongside the layout (not `total_cost_inr=0.0`)

### Frontend Shell (FE-)

- **FE-01**: React SPA (Vite + TypeScript) with drag-drop PDF upload and text prompt input
- **FE-02**: Processing view polls job status and shows progress while pipeline runs
- **FE-03**: Results page renders generated layout as 2D visualization (SVG/Canvas) with rooms colored by type, walls, doors, and fixtures labeled
- **FE-04**: Results page renders BOM as an interactive table with material, qty, unit, rate, amount columns
- **FE-05**: BOM table supports inline editing of quantities and rates with live total recalculation
- **FE-06**: API integration uses hardcoded API key (no auth UI for MVP)

### Export (EXP-)

- **EXP-01**: Export BOM as formatted Excel (.xlsx) with project header, line items, and totals
- **EXP-02**: Export combined report as PDF (layout image + BOM table + project summary)

### Demo Polish (POL-)

- **POL-01**: End-to-end flow completes in <3 minutes (upload → processing → layout + BOM on screen)
- **POL-02**: Loading states, error messages, and transitions are smooth and professional
- **POL-03**: Full demo can run without crashes or manual intervention

### Client Readiness (CR-)

- **CR-01**: Materials CRUD UI — add, edit, delete materials and rates from the frontend
- **CR-02**: Project history — list past uploads, re-open previous results
- **CR-03**: Basic onboarding guidance for first-time upload
- **CR-04**: Deployed to a public URL accessible without local setup

## v2 Requirements (Post-MVP)

- Multi-tenant user accounts and billing
- 3D extrusion visualization
- Contractor correction deltas captured as training data
- Mobile responsive design
- CI/CD pipeline with automated deployment
- Comprehensive edge-case handling for unusual floorplan formats
- Version history / undo for BOM edits
- Real-time collaboration

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| BOM-01 | Phase 2 | Pending |
| BOM-02 | Phase 2 | Pending |
| BOM-03 | Phase 2 | Pending |
| BOM-04 | Phase 2 | Pending |
| BOM-05 | Phase 2 | Pending |
| FE-01 | Phase 3 | Pending |
| FE-02 | Phase 3 | Pending |
| FE-03 | Phase 4 | Pending |
| FE-04 | Phase 4 | Pending |
| FE-05 | Phase 4 | Pending |
| FE-06 | Phase 3 | Pending |
| EXP-01 | Phase 5 | Pending |
| EXP-02 | Phase 5 | Pending |
| POL-01 | Phase 5 | Pending |
| POL-02 | Phase 5 | Pending |
| POL-03 | Phase 5 | Pending |
| CR-01 | Phase 6 | Pending |
| CR-02 | Phase 6 | Pending |
| CR-03 | Phase 6 | Pending |
| CR-04 | Phase 6 | Pending |

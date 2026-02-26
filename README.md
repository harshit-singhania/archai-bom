# ArchAI

**Floorplan-to-BOM: The End of Manual Construction Estimating.**

> Autonomous AI pipeline that converts 2D floorplan PDFs into priced Bills of Materials for commercial interior contractors — compressing 3 weeks of manual CAD work into a 3-minute API call.

---

## The Problem

India's commercial interior fit-out market is exploding, driven by massive corporate expansions — but the way contractors bid on projects is trapped in the dark ages.

Commercial contractors spend 2–5% of total revenue just *estimating* how much a project will cost. When they receive a blank floorplan for a new office fit-out, a team of junior architects spends three weeks manually tracing lines in CAD software and tracking material prices in chaotic spreadsheets.

Worse: they lose **80% of the bids** they spend weeks preparing, because human bottlenecks make them too slow to respond.

---

## The Solution

A massive-ROI tool for the Chief Estimator.

1. **Input** — Upload a blank 2D floorplan PDF and describe the space (`"5,000 sq ft dental clinic with 6 operatories"`)
2. **Generation** — The spatial reasoning engine generates the optimized 2D layout and extrudes the geometry automatically
3. **Output** — The system deterministically parses that geometry and produces an exact Bill of Materials — down to linear feet of electrical wiring and acoustic ceiling tiles — priced to local India market rates

---

## System Architecture

Four decoupled modules:

### Module 1 — Vision & Ingestion Engine

Converts unstructured PDFs into a structured spatial graph. Uses computer vision to extract room boundaries, load-bearing pillars, doors, and scale from messy 2D architectural drawings. Dumb pixels in, structured geometry out.

### Module 2 — Spatial Generation Model

The generative brain. Takes the spatial graph and a natural language prompt, and populates it with walls, desks, and fixtures. Understands that a "conference room" requires different spacing and geometry than a "break room."

### Module 3 — Deterministic Calculator

Generative AI hallucinates; construction math cannot. This module is a strict rules engine — **no AI in the math layer**. It takes geometry as input, applies localized construction math (e.g., `if room = 500 sq ft, calculate X sheets of drywall`), and produces the final priced BOM spreadsheet.

### Module 4 — Client Dashboard

Dual-pane web application. PDF upload on the left, 2D layout visualization and live BOM spreadsheet on the right. Contractor corrections are captured as training deltas — the core of the data moat.

---

## Why This Wins

This is not a generic AI wrapper. Standard LLMs hallucinate measurements and building codes, making their estimates legally useless.

The moat is **proprietary layout-to-cost datasets**. Every time a contractor adjusts the generated BOM — swapping a material grade or fixing a measurement to match local building codes — that delta is captured. The system learns hyper-specific, localized pricing and construction rules that cannot be scraped from the internet.

---

## What's Not In Scope (v1)

- MEP (mechanical, electrical, plumbing) calculations
- Structural engineering
- 3D rendering or BIM integration
- Multi-tenant SaaS features or team collaboration
- International markets (India only)
- Real-time pricing APIs (v1 uses hardcoded local rates)
- Automated permitting or compliance checking

---

## Success Criteria

v1 is done when a real contractor uses it on a live bid and reports measurable time savings with less than 10% manual correction of the generated BOM.

---

## Roadmap

| Phase | Module | Objective |
|-------|--------|-----------|
| 1 | Vision & Ingestion | PDF → structured spatial graph |
| 2 | Spatial Generation | Spatial graph + prompt → 2D layout |
| 3 | Deterministic Calculator | Geometry → priced BOM spreadsheet |
| 4 | Client Dashboard | End-to-end UI + correction capture |

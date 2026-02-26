---
phase: 3
status: complete
updated: 2026-02-26
---

# Phase 3 Research: Deterministic Calculator + Async Job Queue

## Q1: What queue system for async PDF processing?

**Decision: Celery + Redis**

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| Celery + Redis | Battle-tested with Flask, rich retry/monitoring, large ecosystem | Heavier setup, learning curve | **SELECTED** |
| RQ (Redis Queue) | Ultra-simple, Flask-native | No retry policies, limited monitoring, no priority queues | Too simple |
| RabbitMQ | Best at message routing, delivery guarantees | Overkill — we don't need pub/sub or complex routing | Over-engineered |
| Dramatiq | Modern Celery alternative | Smaller community, fewer Flask examples | Risky |

**Rationale:**
- Flask + Celery is the most documented pairing in the Python ecosystem
- Redis serves double duty: message broker + result backend (one dependency)
- Celery provides retry policies (Gemini API flakiness), task priority, monitoring (Flower)
- The workload is simple: fire-and-forget jobs with status polling — Celery handles this natively
- Redis also useful later for caching Gemini responses and rate limiting

**Integration pattern:**
```
Client → POST /api/v1/ingest → returns job_id (202 Accepted)
Client → GET /api/v1/jobs/{job_id} → polls status
Worker → picks up task from Redis → runs ingest_pdf() → stores result
```

## Q2: BOM line item categories for Indian commercial interiors

**Categories identified (India market, commercial fit-out):**

| Category | Unit | Source Geometry | Calculation Rule |
|----------|------|----------------|------------------|
| Gypsum drywall partition | sqft | interior_walls | length × height × 2 sides |
| Metal stud framing | sqft | interior_walls | same as drywall area |
| Flooring | sqft | rooms | room area by room_type → material |
| False ceiling (grid) | sqft | rooms | room area (same as flooring) |
| Interior paint | sqft | walls (both sides) | (perimeter + interior wall area) - door openings |
| Flush doors | piece | doors | count by door_type |
| Glass partition | sqft | interior_walls (glass material) | length × height |
| Electrical points | piece | rooms | rule: points_per_sqft by room_type |
| Skirting/base trim | rft | rooms | room perimeter |
| Blinds/curtains | sqft | rooms (if has windows) | window area estimate |

## Q3: India-market pricing sources (v1 hardcoded)

**Approach:** Hardcode rates from 2024-25 CPWD (Central Public Works Department) Schedule of Rates + market surveys. Allow override per-project.

**Sample rates (INR, 2025):**

| Material | Unit | Rate (₹) | Source |
|----------|------|-----------|--------|
| Gypsum board (12.5mm) | sqft | 55 | CPWD + market |
| Metal stud frame (GI) | sqft | 30 | Market survey |
| Vitrified tiles (600x600) | sqft | 75 | Market survey |
| Carpet tiles (standard) | sqft | 110 | Market survey |
| Grid false ceiling (2x2) | sqft | 70 | CPWD |
| Gypsum false ceiling | sqft | 85 | CPWD |
| Interior emulsion paint | sqft | 12 | Asian Paints MRP |
| Flush door (solid core) | piece | 5500 | Market survey |
| Glass partition (12mm) | sqft | 450 | Market survey |
| Electrical point (5A) | point | 850 | CPWD |
| PVC skirting | rft | 45 | Market survey |

## Q4: Excel export library

**Decision: openpyxl**

- Standard library for .xlsx in Python
- Supports formatting, formulas, multiple sheets
- No heavy dependencies
- Already widely used in construction estimating tools

## Q5: Assumed ceiling height for wall area calculations

**Decision: 10 feet (3048mm) default, configurable per-project**

- Standard Indian commercial interior ceiling height: 9-10 feet
- High-end offices/lobbies: 12 feet
- Make it a parameter in the BOM generation request, default 10ft

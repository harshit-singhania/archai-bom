# DECISIONS.md — Architecture Decision Records

> **Format**: ADR (Architecture Decision Record) log. One entry per significant decision.

---

## ADR-001: MVP Scope — All 4 Modules

**Date:** 2026-02-25
**Status:** Accepted

**Context:** Needed to define MVP scope. Options were math-pipeline-only, ingestion+calculator+dashboard, or full 4-module system.

**Decision:** Build all 4 modules in MVP v1.0, not production-hardened.

**Rationale:** Paying pilot customer requires end-to-end workflow. A partial pipeline cannot be used on a live bid.

**Consequences:** Larger initial scope; compensated by clear phase structure in ROADMAP.md.

---

## ADR-002: No AI in the Math Layer

**Date:** 2026-02-25
**Status:** Accepted

**Context:** BOM accuracy is legally and commercially critical. LLMs hallucinate measurements.

**Decision:** The Deterministic Calculator (Phase 3) must use a rules engine, not LLM generation. AI output (geometry) feeds into it, but the math itself is deterministic.

**Rationale:** Contractor legally relies on these estimates for bids. Hallucinated quantities = lost money + reputation.

**Consequences:** Module 2 (Spatial Generation) and Module 3 (Calculator) must have a clean handoff interface: geometry schema in, quantities out.

---

## ADR-003: Stack Selection Deferred to Research

**Date:** 2026-02-25
**Status:** Pending

**Context:** No strong constraints on stack. Options include Python/FastAPI, Node.js, and various vision model approaches.

**Decision:** Document options in RESEARCH.md before committing.

**Next action:** Complete RESEARCH.md → revisit this ADR.

---

*(Add new ADRs as decisions are made)*

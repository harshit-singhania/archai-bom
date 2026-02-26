# RESEARCH.md — Technology Research

> **Purpose**: Document technology options, trade-offs, and decisions before committing to a stack.

---

## Open Questions

### 1. PDF Ingestion / Computer Vision Approach ✅ DECIDED

**Question:** What is the best approach for extracting room boundaries and spatial graphs from unstructured 2D floorplan PDFs?

**Decision: The Vector PDF Bypass**

For MVP, we establish a golden rule: Users must upload clean CAD-exported PDFs. A clean CAD-exported PDF is not an image; it is a mathematical text file disguised as a document. We extract raw vector math directly rather than using computer vision to guess.

**Execution Plan:**
- **The Vector Extractor**: Use PyMuPDF (fitz) to extract exact (x1, y1) -> (x2, y2) coordinates of every vector line in milliseconds
- **The Layer Filter**: Filter by line thickness/color to distinguish structural walls from dimension lines (heuristic: thick lines = walls)
- **The Semantic Brain**: Send raster screenshot to Google Gemini to extract room names and stated scale (e.g., "1/4" = 1'")
- **The Merge**: Combine exact vector lines with semantic labels to build spatial graph

**Why this wins:**
- Cost: PyMuPDF is free; Google Gemini for text extraction has generous free tier
- Speed: Runs in under 3 seconds
- Accuracy: 100% geometric precision from architect's raw CAD data
- Output: Exact linear footage for BOM calculator immediately

**Risk:** Assumes clean CAD exports; scanned PDFs will fail (acceptable for MVP)

**Status:** Locked. 🔒

---

### 2. Spatial Generation Model ✅ DECIDED

**Question:** What approach generates optimal 2D room layouts from a spatial graph + natural language prompt?

**Decision: LLM + DSL + Constraint Checker with Iterative Refinement**

**The Pipeline:**
1. **The Prompt**: Feed extracted PDF perimeter (via PyMuPDF) + user prompt into Google Gemini
2. **The Generation**: Gemini outputs `layout.json` containing proposed coordinates for every interior wall and door
3. **The Critic (LangGraph)**: Constraint Checker validates JSON:
   - Do rooms overlap? (Shapely polygon intersection)
   - Are corridors too narrow? (Buffer operations)
   - Do door swings clear? (Arc-polygon intersection)
   - If fails, feed error back to Gemini for rewrite (max 3 iterations)
4. **The Render**: JSON passes → render via SVG/Fabric.js on React frontend

**Post-processing:** Snap all coordinates to 50mm construction grid before validation

**Why this wins:**
- DSL (JSON) is auditable, versionable, diffable—critical for ₹50 Lakh estimates
- Separates "creative" generation from "hard rules" validation
- Self-correcting via LangGraph feedback loop
- Vector rendering gives zoom/pan/measurements for BOM workflows

**Fallback:** If max iterations exceeded, fall back to deterministic layout algorithm

**Status:** Locked. 🔒

---

### 3. Backend Framework ✅ DECIDED

**Question:** What backend framework best handles the PDF processing, model inference, and API layer?

**Decision: Python / Flask**

| Option | Verdict | Reason |
|--------|---------|--------|
| Django | ❌ Rejected | Overkill for our needs; built for monolithic CMS with massive relational DB, not high-speed inference engines |
| Node.js | ❌ Rejected | Cannot easily run PyMuPDF, LangGraph, or heavy Pandas natively; would require Python microservice, doubling DevOps overhead |
| FastAPI | ⚠️ Alternative | Great for async, but Flask offers more flexibility and simpler deployment for our specific ML pipeline needs |
| **Flask** | ✅ **Selected** | Lightweight, battle-tested, extensive middleware ecosystem; simpler deployment; perfect for sync ML workloads (PyMuPDF, Google Generative AI); India's massive Flask talent pool |

**Status:** Locked. 🔒

---

### 4. Frontend Framework ✅ DECIDED

**Question:** What frontend framework best supports the dual-pane dashboard (PDF viewer + interactive BOM)?

**Decision: React (via Vite or Next.js SPA)**

We are building a highly interactive, dual-pane productivity tool, not a marketing website. Framework matters less than component ecosystem.

**Component Strategy:**
| Pane | Library | Purpose |
|------|---------|---------|
| Left (PDF) | `react-pdf` | Render uploaded floorplan cleanly |
| Right (BOM) | `ag-grid-react` or `handsontable` | Excel-like, editable grid with instant price updates |

**Why not SvelteKit/Vue:** Would waste 2 weeks building custom PDF viewer and reactive data table from scratch.

**Status:** Locked. 🔒

---

### 5. Competitive Landscape ✅ RESEARCHED

**Question:** What tools do Chief Estimators currently use beyond spreadsheets, and what are the gaps?

#### 1. Legacy "Digital Highlighters" (PlanSwift & Bluebeam Revu)
- **What they do:** Industry standard for PDF takeoff
- **The Gap:** Literally just digital highlighters. To calculate drywall in Bluebeam, a human clicks point A→B→C→D for each room. 50 rooms = 200 clicks. **They digitized paper; they didn't automate work.**
- **AI Presence:** Zero generative AI

#### 2. Enterprise Heavyweights (CostX & ProEst)
- **What they do:** Massive platforms tied to BIM 3D models
- **The Gap:** In India, 95% of mid-market commercial fit-outs use 2D AutoCAD exports, not 3D BIM. CostX requires perfect Revit models—useless for quick, dirty 2D PDFs Indian contractors receive.

#### 3. Local Indian Reality (Excel + WhatsApp)
- **What they do:** Most Indian D&B firms generating ₹50Cr use cracked AutoCAD for measurements, then manually type into fragile Excel templates
- **The Pricing Gap:** PlanSwift charges ~$1,750 USD/license. Indian mid-market contractors balk at US enterprise SaaS pricing for tools that don't understand **Delhi Schedule of Rates (DSR)** or local vendor pricing in INR.

#### ArchAI's Wedge
**No one is doing: Automated 2D Vector Extraction → Localized Indian Pricing Math**

- PlanSwift = digital ruler
- ArchAI = autonomous estimating agent
- We don't sell a better PDF viewer; we sell a completed ₹50 Lakh estimate in 60 seconds

**Status:** Locked. 🔒

---

## Decisions Summary

| # | Question | Decision | Key Tools |
|---|----------|----------|-----------|
| 1 | PDF Ingestion | Vector PDF Bypass | PyMuPDF + Google Gemini |
| 2 | Spatial Generation | LLM + DSL + Constraint Checker | Google Gemini + Shapely + Constraint Loop + SVG |
| 3 | Backend Framework | Python / FastAPI | FastAPI + async Python |
| 4 | Frontend Framework | React SPA | React + react-pdf + ag-grid-react |
| 5 | Competitive Position | Autonomous agent vs. digital ruler | Speed + India pricing localization |

---

*Last updated: 2026-02-25*

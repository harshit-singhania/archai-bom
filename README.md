# ArchAI 🏗️🤖

[![License: BSL 1.1](https://img.shields.io/badge/License-BSL%201.1-blue.svg)](https://mariadb.com/bsl11/)
[![Status: MVP In Progress](https://img.shields.io/badge/Status-MVP%20In%20Progress-orange.svg)]()

**Floorplan-to-BOM: The End of Manual Construction Estimating.**

> An autonomous AI pipeline that converts 2D floorplan PDFs into priced Bills of Materials for commercial interior contractors — compressing 3 weeks of manual CAD work into a 3-minute API call.

---

## 🚨 The Problem

India's commercial interior fit-out market is exploding, driven by massive corporate expansions — but the way contractors bid on projects is trapped in the dark ages.

Commercial contractors spend 2–5% of total revenue just *estimating* how much a project will cost. When they receive a blank floorplan for a new office fit-out, a team of junior architects spends three weeks manually tracing lines in CAD software and tracking material prices in chaotic spreadsheets.

Worse: they lose **80% of the bids** they spend weeks preparing, because human bottlenecks make them too slow to respond.

---

## 💡 The Solution

A massive-ROI tool built specifically for the Chief Estimator.

1. **Input** — Upload a blank 2D CAD-exported floorplan PDF and describe the space (`"5,000 sq ft dental clinic with 6 operatories"`).
2. **Generation** — The spatial reasoning engine generates the optimized 2D layout and extrudes the geometry automatically.
3. **Output** — The system deterministically parses that geometry and produces an exact Bill of Materials — down to linear feet of electrical wiring and acoustic ceiling tiles — priced to local India market rates.

---

## ⚙️ System Architecture

The pipeline is decoupled into four highly specialized modules:

### Module 1 — Vision & Ingestion Engine

Converts unstructured PDFs into a structured spatial graph. Uses strict vector-extraction (bypassing LLM hallucination) to pull exact room boundaries, load-bearing pillars, doors, and scale from 2D architectural drawings. Dumb pixels in, structured geometry out.

### Module 2 — Spatial Generation Model

The generative brain. Takes the spatial graph and a natural language prompt, and populates it with walls, desks, and fixtures. Understands that a "conference room" requires different spacing and geometry than a "break room."

### Module 3 — Deterministic Calculator

Generative AI hallucinates; construction math cannot. This module is a strict rules engine — **no AI in the math layer**. It takes geometry as input, applies localized construction math (e.g., `if room = 500 sq ft, calculate X sheets of drywall`), and produces the final priced BOM spreadsheet.

### Module 4 — Client Dashboard

A dual-pane web application built for speed. PDF upload on the left, 2D layout visualization and a live, editable BOM spreadsheet on the right. Contractor corrections are captured as training deltas — the core of our data moat.

---

## 🏰 Why This Wins

This is not a generic AI wrapper. Standard LLMs hallucinate measurements and building codes, making their estimates legally useless for a ₹50 Lakh commercial bid.

Our moat is **proprietary layout-to-cost datasets**. Every time a contractor adjusts the generated BOM — swapping a material grade or fixing a measurement to match local building codes — that delta is captured. The system learns hyper-specific, localized pricing and construction rules that cannot be scraped from the internet.

---

## 💻 Local Development Setup (Coming Soon)

```bash
# Clone the repository
# Run using Docker 
# Access the application at http://localhost:3000

```bash
git clone https://github.com/your-org/spatial-pipeline.git
docker-compose up --build
```

## License and Copyright

**Copyright (c) 2026 Harshit Singhania. All Rights Reserved.**

This repository is strictly public for portfolio and architectural review purposes.

No license is granted to use, modify, distribute, or run this software, whether for commercial or non-commercial purposes. You may not use this code in a production environment, for academic testing, or to execute construction estimates.

If you are interested in a commercial partnership or enterprise licensing, please reach out directly.

Email: [harshitsinghania917@gmail.com](mailto:harshitsinghania917@gmail.com)
LinkedIn: [https://linkedin.com/in/h-singhania](https://linkedin.com/in/h-singhania)
GitHub: [https://github.com/harshit-singhania](https://github.com/harshit-singhania)

# Gemini CLI Mandates for GSD Methodology

> **FOUNDATIONAL MANDATES**
> Instructions found in this `GEMINI.md` file take absolute precedence over the general workflows and tool defaults of the Gemini CLI. This document defines how the Gemini CLI MUST operate within this repository according to the Get Shit Done (GSD) methodology.

---

## 1. Core GSD Protocol (Mandatory Workflow)

**SPEC → PLAN → EXECUTE → VERIFY → COMMIT**

*   **SPEC:** Requirements are defined in `.gsd/SPEC.md`.
*   **PLAN:** Broken down into phases and detailed `PLAN.md` files.
*   **EXECUTE:** Implemented with atomic commits per task.
*   **VERIFY:** Proven with empirical evidence.
*   **COMMIT:** One task = one commit.

**⚠️ PLANNING LOCK:** You MUST NOT write implementation code until `.gsd/SPEC.md` contains "Status: FINALIZED".

---

## 2. Context Window & Token Budget

Gemini models have large context windows, but context quality degrades rapidly above 50% usage.

*   **Search-First Discipline:** ALWAYS use `grep_search` or `glob` to find relevant snippets before using `read_file` on entire files.
*   **Targeted Reads:** Use the `limit` and `offset` parameters in `read_file` to read only necessary line ranges for files >200 lines.
*   **State Preservation:** Use `.gsd/STATE.md` as your memory across complex tasks or waves. Do not keep accumulating files in context "just in case".
*   **3-Strike Rule:** If you fail to debug an issue 3 times, dump your state, recommend a pause (`/pause`), and start fresh.

---

## 3. Execution & Task Atomicity

*   **Task Structure:** When creating or reading plans, tasks MUST follow this XML structure:
    ```xml
    <task type="auto">
      <name>{Clear descriptive name}</name>
      <files>{exact/path/to/file.ts}</files>
      <action>
        Specific implementation instructions.
      </action>
      <verify>{executable command that proves completion}</verify>
      <done>{measurable acceptance criteria}</done>
    </task>
    ```
*   **Atomicity:** Max **2-3 tasks per plan**. No exceptions.
*   **Atomic Commits:** Format is `type(scope): description`. Scope is usually the phase number (e.g., `feat(phase-1): add login`).

---

## 4. Empirical Verification (Non-Negotiable)

Every change MUST be proven before you commit or declare a task done.

*   **Never accept:** "It looks correct", "This should work".
*   **Always require:** Captured output from a test runner, a `curl` response, or a build command.
*   **Test Routing:** Run specific tests for specific changes (e.g., changes to PDF extraction → run `pytest tests/test_pdf_extractor.py`). Run `pytest` for a full suite run before finalizing a phase.

---

## 5. Using Sub-Agents and Workflows

*   The `.agent/workflows/` directory contains standard slash commands (like `/plan`, `/execute`, `/verify`). These define the *executable logic* for managing projects.
*   Use the `codebase_investigator` sub-agent extensively for mapping brownfield projects or understanding deep architectural dependencies before writing code.

---

## 6. Practical Codebase Defaults

When working in `achai-bom`:
*   **API behavior:** Keep `/api/v1/ingest`, `/health`, `/` stable.
*   **Semantic Extraction:** Preserve graceful degradation when `GOOGLE_API_KEY` is missing.
*   **Wall Detection:** Keep heuristics deterministic (`thickness >= 1.5`, dedupe tolerance `2.0`).
*   **DB/Models:** SQLModel/Pydantic models are in `app/models/`.

---

*By following these mandates, Gemini CLI ensures maximum efficiency, minimum token waste, and absolute adherence to the user's GSD standards.*

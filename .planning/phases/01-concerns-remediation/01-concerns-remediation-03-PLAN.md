---
phase: 01-concerns-remediation
plan: 03
type: execute
wave: 1
depends_on: []
files_modified:
  - requirements.txt
  - requirements.in
  - requirements-lock.txt
  - Dockerfile
  - scripts/validate-all.sh
autonomous: true
requirements:
  - DEP-01
must_haves:
  truths:
    - "Dependency installation is deterministic across local, CI, and container builds"
    - "requirements.txt no longer drifts silently due to loose >= resolution"
  artifacts:
    - path: requirements.in
      provides: "Human-maintained direct dependency input set"
    - path: requirements-lock.txt
      provides: "Fully pinned resolved dependency lock"
    - path: Dockerfile
      provides: "Container install path that uses lockfile"
  key_links:
    - from: requirements.in
      to: requirements-lock.txt
      via: "pip-compile"
      pattern: "pip-compile"
    - from: requirements-lock.txt
      to: Dockerfile
      via: "pip install -r"
      pattern: "requirements-lock.txt"
---

<objective>
Introduce deterministic dependency management to remove reproducibility drift.

Purpose: Prevent transitive version surprises and ensure stable deploy/test outcomes.
Output: pip-tools workflow, pinned lockfile, and container/runtime install updates.
</objective>

<execution_context>
@/Users/harshit/.config/opencode/get-shit-done/workflows/execute-plan.md
@/Users/harshit/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/codebase/CONCERNS.md
@requirements.txt
@Dockerfile
@scripts/validate-all.sh
</context>

<tasks>

<task type="auto">
  <name>Task 1: Split direct dependencies from resolved lock set</name>
  <files>requirements.in, requirements-lock.txt, requirements.txt</files>
  <action>Create requirements.in from current first-order dependencies, generate requirements-lock.txt with pinned versions (including transitive dependencies), and keep requirements.txt as a compatibility shim or alias to avoid breaking existing scripts. Document lock regeneration command in file comments.</action>
  <verify>
    <automated>python -m piptools compile requirements.in --output-file requirements-lock.txt</automated>
  </verify>
  <done>Pinned lockfile exists and can be deterministically regenerated from requirements.in.</done>
</task>

<task type="auto">
  <name>Task 2: Switch runtime and validation scripts to lockfile installs</name>
  <files>Dockerfile, scripts/validate-all.sh</files>
  <action>Update Docker build dependency install to use requirements-lock.txt and ensure validation tooling checks lockfile presence/consistency before running other validations.</action>
  <verify>
    <automated>docker build -t achai-bom:lockcheck .</automated>
  </verify>
  <done>Container builds from pinned dependencies and validation scripts enforce lockfile workflow.</done>
</task>

</tasks>

<verification>
Rebuild image and confirm repeat builds use identical dependency versions.
</verification>

<success_criteria>
DEP-01 is resolved with a pinned lock artifact used in runtime installation paths.
</success_criteria>

<output>
After completion, create `.planning/phases/01-concerns-remediation/01-concerns-remediation-03-SUMMARY.md`
</output>

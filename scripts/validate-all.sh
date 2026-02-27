#!/bin/bash
# GSD Master Validation Script
# Runs all validators and reports overall status

total_errors=0
script_dir="$(dirname "$0")"

echo ""
echo "╔═══════════════════════════════════════════════════════╗"
echo "║         GSD ► RUNNING ALL VALIDATORS                  ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""

# ── Lockfile presence check ──────────────────────────────────────────────────
echo "▶ Checking lockfile presence (DEP-01)..."

REPO_ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel 2>/dev/null || echo "$(dirname "$0")/..")"

if [ ! -f "$REPO_ROOT/requirements.in" ]; then
    echo "  ❌ requirements.in not found — run: pip-compile requirements.in --output-file requirements-lock.txt --strip-extras"
    ((total_errors++))
elif [ ! -f "$REPO_ROOT/requirements-lock.txt" ]; then
    echo "  ❌ requirements-lock.txt not found — regenerate with: pip-compile requirements.in --output-file requirements-lock.txt --strip-extras"
    ((total_errors++))
elif [ "$REPO_ROOT/requirements.in" -nt "$REPO_ROOT/requirements-lock.txt" ]; then
    echo "  ⚠️  requirements.in is newer than requirements-lock.txt — lockfile may be stale"
    echo "     Regenerate with: pip-compile requirements.in --output-file requirements-lock.txt --strip-extras"
    # Stale lockfile is a warning, not a hard error — continue but note it
else
    echo "  ✅ Lockfile present and up to date"
fi

echo ""

# ── Run workflow validator ────────────────────────────────────────────────────
echo "▶ Running workflow validation..."
"$script_dir/validate-workflows.sh"
if [ $? -ne 0 ]; then ((total_errors++)); fi
echo ""

# ── Run skill validator ───────────────────────────────────────────────────────
echo "▶ Running skill validation..."
"$script_dir/validate-skills.sh"
if [ $? -ne 0 ]; then ((total_errors++)); fi
echo ""

# ── Run template validator ────────────────────────────────────────────────────
echo "▶ Running template validation..."
"$script_dir/validate-templates.sh"
if [ $? -ne 0 ]; then ((total_errors++)); fi
echo ""

# ── Summary ───────────────────────────────────────────────────────────────────
echo "╔═══════════════════════════════════════════════════════╗"
echo "║                    SUMMARY                            ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""

if [ $total_errors -eq 0 ]; then
    echo "✅ All validators passed!"
    exit 0
else
    echo "❌ $total_errors validator(s) failed"
    exit 1
fi

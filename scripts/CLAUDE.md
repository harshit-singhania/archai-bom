# ArchAI BOM — Claude Guidelines (scripts/)

## Context

You are in the `scripts/` directory containing utility and validation scripts.

## GSD Workflow (MANDATORY)

**Follow GSD for all script work:**

1. **Context**:
   - Read `../.planning/STATE.md` — script requirements
   - Read `../CLAUDE.md` — full guidelines
   - Check existing script patterns

2. **Planning**:
   - Define script purpose and interface
   - Plan error handling and validation
   - Update `.planning/STATE.md`

3. **Execution**:
   - Write clear, commented code
   - Handle errors gracefully
   - Follow existing patterns

4. **Validation**:
   - Test script execution
   - Verify error handling
   - Update `.planning/STATE.md`

## Script Standards

### Bash Scripts
```bash
#!/bin/bash
set -euo pipefail  # Strict mode

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log_info() { echo "[INFO] $*"; }
log_error() { echo "[ERROR] $*" >&2; }

cleanup() {
    # Cleanup logic
}
trap cleanup EXIT

main() {
    # Main logic
}

main "$@"
```

### Python Scripts
```python
#!/usr/bin/env python3
"""One-line description."""

import argparse
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main() -> int:
    parser = argparse.ArgumentParser(description="Script description")
    args = parser.parse_args()
    
    try:
        # Logic here
        return 0
    except Exception as e:
        logger.error(f"Failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

## Validation Scripts

- Must exit 0 on success, non-zero on failure
- Clear error messages
- Count and report errors
- Handle missing files gracefully (nullglob)

## References

- Full: `../CLAUDE.md`
- Agent: `../AGENTS.md`
- App: `../app/CLAUDE.md`

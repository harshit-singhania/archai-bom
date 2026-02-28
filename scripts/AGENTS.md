# ArchAI BOM — Agent Guidelines (scripts/)

## Context

You are in the `scripts/` directory containing utility scripts.

## GSD Workflow (REQUIRED)

**Before modifying scripts:**

1. Read `../.planning/STATE.md` — current phase and script requirements
2. Read `../.planning/PROJECT.md` — architectural context
3. Read `../AGENTS.md` — full agent guidelines
4. Follow GSD protocol:
   - Plan: Define script purpose and interface
   - Execute: Write/modify with clear comments
   - Validate: Test script execution
   - State: Update `.planning/STATE.md`

## Script Conventions

- **Bash scripts**: `#!/bin/bash`, `set -euo pipefail`
- **Python scripts**: `#!/usr/bin/env python3`, type hints
- **Comments**: Explain WHY, not just WHAT
- **Error handling**: Exit with non-zero on failure
- **Help text**: `-h` or `--help` flag

## Key Scripts

```
scripts/
├── setup_supabase_schema.py    # DB schema and seed data
├── validate-all.sh             # Master validation runner
├── validate-workflows.sh       # Workflow file validator
├── validate-skills.sh          # Skill validator
└── validate-templates.sh       # Template validator
```

## Writing Scripts

### Bash
```bash
#!/bin/bash
set -euo pipefail

script_dir="$(dirname "$0")"
error_count=0

main() {
    echo "Starting script..."
    # Logic here
}

main "$@"
```

### Python
```python
#!/usr/bin/env python3
"""Script description."""

import sys
from pathlib import Path

def main() -> int:
    """Main entry point."""
    # Logic here
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

## Testing Scripts

```bash
# Test bash script
bash scripts/validate-all.sh

# Test Python script
python scripts/setup_supabase_schema.py --dry-run
```

## References

- Root: `../AGENTS.md`
- Root: `../CLAUDE.md`
- App: `../app/AGENTS.md`

# CLI Reference

## Overview

ContextCurator provides a command-line interface (`curator`) for managing code dependency graphs.

## Installation

```bash
pip install -e .
```

Verify installation:
```bash
curator --version
```

## Global Options

- `--version, -v`: Show version and exit
- `--verbose`: Enable verbose logging (DEBUG level)
- `--help`: Show help message

## Commands

### `curator init`

Initialize a code map for a project.

**Syntax:**
```bash
curator init [PATH]
```

**Arguments:**
- `PATH`: Project root directory to scan (default: `.`)

**Behavior:**
- Creates `.codemap/` directory
- Scans all Python files in project
- Builds dependency graph
- Saves `graph.json` and `metadata.json`
- Shows progress indicator during scan

**Output:**
```
Scanning /path/to/project...
Created code map: 42 nodes, 17 edges
Saved to /path/to/project/.codemap/graph.json
```

**Error Cases:**
- Path does not exist: Exit code 2
- Path is not a directory: Exit code 2

---

### `curator update`

Update code map with incremental changes.

**Syntax:**
```bash
curator update [--quiet]
```

**Options:**
- `--quiet, -q`: Suppress output on success

**Behavior:**
- Detects file changes since last build
- Updates graph incrementally
- Uses lock file to prevent concurrent execution
- Updates `metadata.json` with new timestamp

**Output (normal):**
```
Updated: 2 modified, 1 added, 0 deleted
```

**Output (quiet):**
```
(no output on success)
```

**Error Cases:**
- `.codemap/` not found: Exit code 1, suggests `curator init`
- `graph.json` invalid: Exit code 1
- Update already in progress: Exit code 0 (skips)

---

### `curator status`

Display code map status and statistics.

**Syntax:**
```bash
curator status
```

**Behavior:**
- Searches for `.codemap/` in current and parent directories
- Loads graph and metadata
- Displays formatted table with Rich

**Output:**
```
┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Metric      ┃ Value                  ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Nodes       │ 42                     │
│ Edges       │ 17                     │
│ Last update │ 2024-01-15T10:30:00Z   │
│ Commit      │ abc123de               │
└─────────────┴────────────────────────┘
```

**Error Cases:**
- `.codemap/` not found: Exit code 1
- `graph.json` not found: Exit code 1
- `graph.json` invalid: Exit code 1

---

### `curator install-hook`

Install git post-commit hook for automatic updates.

**Syntax:**
```bash
curator install-hook
```

**Behavior:**
- Searches for `.git/` in current and parent directories
- Creates or modifies `.git/hooks/post-commit`
- Preserves existing hook content
- Makes hook executable
- Uses absolute path to curator

**Hook Content:**
```bash
#!/bin/sh
# curator-hook-start
# ContextCurator: Auto-update code map after commit
/usr/local/bin/curator update --quiet > /dev/null 2>&1 &
# curator-hook-end
```

**Output:**
```
Installed post-commit hook to /path/to/project/.git/hooks/post-commit
```

**Error Cases:**
- Not a git repository: Exit code 1
- Permission denied: Exit code 1

**Notes:**
- Idempotent: running multiple times is safe
- Hook runs in background (non-blocking)
- Output redirected to `/dev/null`

---

### `curator uninstall-hook`

Remove curator post-commit hook.

**Syntax:**
```bash
curator uninstall-hook
```

**Behavior:**
- Removes lines between `# curator-hook-start` and `# curator-hook-end`
- Preserves other hook content
- Deletes hook file if only curator code

**Output:**
```
Removed curator hook from post-commit.
```

or

```
Removed post-commit hook (was curator-only).
```

**Error Cases:**
- Not a git repository: Exit code 1

**Notes:**
- Succeeds even if hook doesn't exist
- Succeeds even if curator not installed in hook

---

## Troubleshooting

### "Error: .codemap/ not found"

**Solution:** Run `curator init` first to create the code map.

### "Error: Not a git repository"

**Solution:** Initialize git repository with `git init` before installing hook.

### "Update already in progress"

**Cause:** Another `curator update` process is running.

**Solution:** Wait for the other process to complete, or remove `.codemap/.update.lock` if stale.

### Hook not running after commit

**Possible causes:**
1. Hook not executable: `chmod +x .git/hooks/post-commit`
2. Curator not in PATH: Check hook uses absolute path
3. `.codemap/` not initialized: Run `curator init`

**Debug:**
```bash
# Test hook manually
.git/hooks/post-commit
```

### Progress indicator not showing

**Cause:** Terminal doesn't support Rich formatting.

**Solution:** Use `--verbose` flag for text-based output.

---

## Examples

### Basic Workflow

```bash
# Initialize project
cd /path/to/project
curator init .

# Check status
curator status

# Make changes
echo "def new_func(): pass" >> src/main.py

# Update manually
curator update

# Check status again
curator status
```

### Git Hook Workflow

```bash
# Initialize and install hook
curator init .
curator install-hook

# Make changes and commit
git add .
git commit -m "Add feature"
# Hook runs automatically in background

# Check status
curator status
```

### CI/CD Integration

```bash
# In CI pipeline
pip install -e .
curator init .
curator status

# Fail if graph has errors
if [ $? -ne 0 ]; then
    echo "Code map validation failed"
    exit 1
fi
```

### Testing in CI/CD

```bash
# GitHub Actions example
- name: Verify code map
  run: |
    pip install -e .
    curator init .
    curator status

    # Fail if graph is empty (no code detected)
    if curator status | grep -q "Nodes.*0"; then
      echo "ERROR: No code detected in map"
      exit 1
    fi
```

### Local Development with Auto-Update

```bash
# One-time setup
curator init .
curator install-hook

# Normal development workflow
git add .
git commit -m "Add feature"
# Hook automatically updates map in background

# Check map anytime
curator status
```

---

## Configuration

### `.codemap/` Directory Structure

```
.codemap/
├── graph.json       # Serialized dependency graph
├── metadata.json    # Build metadata
└── .update.lock     # Lock file for concurrent updates
```

### `metadata.json` Format

```json
{
  "build_time": "2024-01-15T10:30:00+00:00",
  "commit_hash": "abc123def456789"
}
```

### Environment Variables

None currently supported.

---

## Exit Codes

- `0`: Success
- `1`: Error (e.g., .codemap/ not found, invalid graph)
- `2`: Invalid arguments (e.g., path not found)

---

## Performance

### Initialization

- **Small projects** (<100 files): <1s
- **Medium projects** (100-1000 files): 1-5s
- **Large projects** (>1000 files): 5-30s

### Updates

- **Incremental updates**: <1s (only changed files)
- **Full rebuild**: Same as initialization

### Lock Timeout

- **Default**: 0s (non-blocking)
- **Behavior**: Skips update if lock held

---

## See Also

- [API Documentation](api.md)
- [Architecture Overview](index.md)

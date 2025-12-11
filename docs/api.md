# API Reference

Automatically generated API documentation from source code docstrings.

## Core Module

::: codemap.core
    options:
      show_root_heading: true
      show_source: true
      members_order: source

## Scout Module

### codemap.scout

::: codemap.scout
    options:
      show_root_heading: true
      show_source: true
      members_order: source

#### TreeGenerator

Generate visual tree representation of directory structures with unlimited depth traversal. Returns a `TreeReport` object containing the tree visualization and statistics.

**Usage:**

```python
from pathlib import Path
from codemap.scout import TreeGenerator, TreeReport

generator = TreeGenerator()
report: TreeReport = generator.generate(Path("./project"))

# Access statistics
print(f"Files: {report.total_files}")
print(f"Folders: {report.total_folders}")
print(f"Estimated tokens: {report.estimated_tokens}")

# Print tree visualization
print(report.tree_string)
```

**Output Example:**

```
project/
├── README.md
└── src/
    ├── main.py
    └── utils/
        └── helper.py

Files: 3, Folders: 2, Estimated tokens: 28
```

#### TreeReport

Immutable dataclass containing tree visualization and statistics. Instances are frozen and cannot be modified after creation.

**Fields:**

- `tree_string` (str): Visual tree structure in Unix tree style
- `total_files` (int): Count of scanned files
- `total_folders` (int): Count of scanned directories
- `estimated_tokens` (int): Token estimation (`int(len(tree_string) / 3.5)`)

**Parameters (TreeGenerator.generate):**

- `root_path` (Path): Root directory to scan

**Features:**

- Unlimited depth traversal (no artificial limits)
- `.gitignore` pattern support via pathspec library
- Cross-platform compatibility (Windows/Linux/macOS)

**Ignored Directories (hard-coded):**

- `.git`
- `.venv`
- `__pycache__`

**Ignored Files (hard-coded):**

- `.gitignore` (meta-file, patterns still applied)

<!-- Additional module references will be added here as the project grows -->
<!-- ::: codemap.parsers -->
<!-- ::: codemap.utils -->

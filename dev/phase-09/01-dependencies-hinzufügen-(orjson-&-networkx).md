I have created the following plan after thorough exploration and analysis of the codebase. Follow the below plan verbatim. Trust the files and references. Do not re-verify what's written in the plan. Explore only when absolutely necessary. First implement all the proposed file changes and then I'll review all the changes together at the end.

## Observations

The `requirements-dev.txt` file follows a clear structure with three sections: Core Dependencies, TDD/QA Tools, and Documentation. Core dependencies use version constraints (e.g., `>=2.0.0`) while testing/documentation tools are unpinned. The file uses comment headers and blank lines for section separation. Currently, there are 6 core dependencies including pydantic, tree-sitter, tree-sitter-language-pack, pathspec, and openai.

## Approach

Add `orjson>=3.9.0` and `networkx>=3.0.0` to the Core Dependencies section of `file:requirements-dev.txt`, maintaining alphabetical ordering within the section and consistent version constraint formatting. Both libraries are performance-critical dependencies: orjson for fast JSON serialization and networkx for graph operations in the mapper optimization phase.

## Implementation Steps

### 1. Update requirements-dev.txt

Locate the Core Dependencies section in `file:requirements-dev.txt` (lines 1-6) and add the two new dependencies:

- Insert `networkx>=3.0.0` after line 5 (after `pathspec`)
- Insert `orjson>=3.9.0` after line 4 (after `openai>=1.0.0`)

The resulting Core Dependencies section should maintain alphabetical order and consistent formatting with existing entries.

### 2. Installation Command

After updating the file, execute the following command to install the new dependencies:

```bash
pip install -r requirements-dev.txt
```

Alternatively, for faster installation of only the new packages:

```bash
pip install orjson>=3.9.0 networkx>=3.0.0
```

### Summary Table

| Dependency | Version | Purpose |
|------------|---------|---------|
| orjson | >=3.9.0 | Fast JSON serialization for CodeNode models |
| networkx | >=3.0.0 | Graph operations for dependency analysis |
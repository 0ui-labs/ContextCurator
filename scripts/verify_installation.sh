#!/bin/bash
set -e

echo "=== Verifying curator installation ==="

# Check curator is in PATH
if ! command -v curator &> /dev/null; then
    echo "ERROR: curator command not found"
    exit 1
fi

# Check version
curator --version

# Check help
curator --help

# Test in temporary directory
TMPDIR=$(mktemp -d)
cd "$TMPDIR"

# Create sample project
mkdir -p src
echo "def hello(): pass" > src/main.py

# Test init
curator init .
if [ ! -d ".codemap" ]; then
    echo "ERROR: .codemap not created"
    exit 1
fi

# Test status
curator status

# Test update
curator update

echo "=== Installation verified successfully ==="
rm -rf "$TMPDIR"

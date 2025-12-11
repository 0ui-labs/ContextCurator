#!/bin/bash
# Thin wrapper script for Unix convenience.
# Single source of truth: setup_check.py
#
# Usage: ./setup_check.sh
# Equivalent to: python setup_check.py

set -euo pipefail

exec python setup_check.py "$@"

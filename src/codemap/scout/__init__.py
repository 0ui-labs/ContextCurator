"""Scout module for code exploration and visualization.

This module provides tools for exploring and visualizing code structures,
including tree generation with TreeReport objects containing statistics,
and LLM-powered analysis for identifying non-source files/folders.
"""

from codemap.scout.advisor import StructureAdvisor
from codemap.scout.models import TreeReport
from codemap.scout.tree import TreeGenerator

__all__ = ["TreeGenerator", "TreeReport", "StructureAdvisor"]

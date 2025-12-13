"""Tree-sitter query definitions for Python code parsing.

This module contains S-expression queries for extracting structural elements
(classes, functions) and dependencies (imports) from Python source code.

Query syntax uses tree-sitter's pattern matching with captures (@name).
See: https://tree-sitter.github.io/tree-sitter/using-parsers/queries
"""

# Query for function definitions
# Captures function name from function_definition nodes
PYTHON_FUNCTION_QUERY = """
(function_definition
  name: (identifier) @function.name)
"""

# Query for class definitions
# Captures class name from class_definition nodes
PYTHON_CLASS_QUERY = """
(class_definition
  name: (identifier) @class.name)
"""

# Query for import statements
# Captures module name from both 'import x' and 'from x import y'
PYTHON_IMPORT_QUERY = """
(import_statement
  name: (dotted_name) @import.name)

(import_from_statement
  module_name: (dotted_name) @import.module)
"""

# Combined query for all Python structures
# Used by ParserEngine to extract all nodes in one pass
PYTHON_ALL_QUERY = """
(function_definition
  name: (identifier) @function.name)

(class_definition
  name: (identifier) @class.name)

(import_statement
  name: (dotted_name) @import.name)

(import_from_statement
  module_name: (dotted_name) @import.module)
"""

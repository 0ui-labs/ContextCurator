"""Unit tests for mapper.models module."""

import pytest
from pathlib import Path
from dataclasses import FrozenInstanceError

from codemap.mapper.models import CodeNode


class TestCodeNode:
    """Test suite for CodeNode dataclass."""

    def test_codenode_creation(self):
        """Test CodeNode can be instantiated with all attributes."""
        node = CodeNode(
            type="function",
            name="foo",
            start_line=1,
            end_line=3
        )
        assert node.type == "function"
        assert node.name == "foo"
        assert node.start_line == 1
        assert node.end_line == 3

    def test_codenode_is_frozen(self):
        """Test CodeNode is immutable (frozen)."""
        node = CodeNode(type="function", name="foo", start_line=1, end_line=3)
        with pytest.raises(FrozenInstanceError):
            node.name = "bar"

    def test_codenode_equality(self):
        """Test CodeNode equality comparison."""
        node1 = CodeNode(type="function", name="foo", start_line=1, end_line=3)
        node2 = CodeNode(type="function", name="foo", start_line=1, end_line=3)
        node3 = CodeNode(type="function", name="bar", start_line=1, end_line=3)
        assert node1 == node2
        assert node1 != node3

    def test_codenode_all_attributes_accessible(self):
        """Test all CodeNode attributes are accessible."""
        node = CodeNode(type="class", name="MyClass", start_line=5, end_line=15)
        # Verify all attributes can be read
        assert hasattr(node, "type")
        assert hasattr(node, "name")
        assert hasattr(node, "start_line")
        assert hasattr(node, "end_line")
        # Verify values
        assert node.type == "class"
        assert node.name == "MyClass"
        assert node.start_line == 5
        assert node.end_line == 15

    def test_codenode_different_types(self):
        """Test CodeNode with various node types."""
        class_node = CodeNode(type="class", name="MyClass", start_line=1, end_line=10)
        function_node = CodeNode(type="function", name="my_func", start_line=15, end_line=20)
        import_node = CodeNode(type="import", name="os", start_line=1, end_line=1)

        assert class_node.type == "class"
        assert function_node.type == "function"
        assert import_node.type == "import"

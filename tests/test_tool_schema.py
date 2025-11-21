"""Tests for tool schema system."""

from aba.tool_schema import ToolParameter, ToolSchema, tool


def test_tool_decorator_extracts_schema():
    """Test that @tool decorator extracts schema from function."""
    @tool
    def example_func(name: str, count: int = 5) -> str:
        """Do something with a name.

        Args:
            name: The name to process
            count: Number of times (default: 5)
        """
        return f"{name} x {count}"

    # Result should be a ToolSchema
    assert isinstance(example_func, ToolSchema)
    assert example_func.name == "example_func"
    assert "Do something with a name" in example_func.description
    assert len(example_func.parameters) == 2

    # Check first parameter (required)
    param1 = example_func.parameters[0]
    assert param1.name == "name"
    assert param1.type == "string"
    assert "name to process" in param1.description
    assert param1.required is True

    # Check second parameter (optional)
    param2 = example_func.parameters[1]
    assert param2.name == "count"
    assert param2.type == "integer"
    assert "Number of times" in param2.description
    assert param2.required is False


def test_tool_decorator_preserves_function():
    """Test that decorated function still works."""
    @tool
    def add(a: int, b: int) -> int:
        """Add two numbers.

        Args:
            a: First number
            b: Second number
        """
        return a + b

    # Function should still be callable
    result = add.function(3, 4)
    assert result == 7


def test_tool_schema_to_openrouter_format():
    """Test conversion to OpenRouter function calling format."""
    schema = ToolSchema(
        name="test_tool",
        description="A test tool",
        function=lambda x: x,
        parameters=[
            ToolParameter(name="query", type="string", description="Search query", required=True),
            ToolParameter(name="limit", type="integer", description="Result limit", required=False)
        ]
    )

    result = schema.to_openrouter_format()

    # Check structure
    assert result["type"] == "function"
    assert result["function"]["name"] == "test_tool"
    assert result["function"]["description"] == "A test tool"

    # Check parameters
    params = result["function"]["parameters"]
    assert params["type"] == "object"
    assert "query" in params["properties"]
    assert "limit" in params["properties"]
    assert params["required"] == ["query"]


def test_tool_decorator_skips_private_params():
    """Test that parameters starting with _ are skipped."""
    @tool
    def internal_func(name: str, _manager=None) -> str:
        """Function with internal param.

        Args:
            name: Public parameter
            _manager: Internal parameter (should be skipped)
        """
        return name

    # Should only have one parameter (name)
    assert len(internal_func.parameters) == 1
    assert internal_func.parameters[0].name == "name"


def test_tool_decorator_handles_various_types():
    """Test that decorator handles different Python types."""
    @tool
    def typed_func(
        text: str,
        number: int,
        decimal: float,
        flag: bool,
        items: list
    ) -> str:
        """Function with various types.

        Args:
            text: A string
            number: An integer
            decimal: A float
            flag: A boolean
            items: A list
        """
        return "ok"

    params = {p.name: p.type for p in typed_func.parameters}
    assert params["text"] == "string"
    assert params["number"] == "integer"
    assert params["decimal"] == "number"
    assert params["flag"] == "boolean"
    assert params["items"] == "array"

"""Tool schema definitions for function calling.

Provides a decorator system inspired by LangChain's @tool pattern,
but adapted for OpenRouter's function calling API format.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, Callable, get_type_hints


@dataclass
class ToolParameter:
    """Parameter definition for a tool."""

    name: str
    type: str
    description: str
    required: bool = True


@dataclass
class ToolSchema:
    """Schema for a tool compatible with OpenRouter function calling."""

    name: str
    description: str
    function: Callable
    parameters: list[ToolParameter] = field(default_factory=list)

    def __call__(self, *args, **kwargs):
        """Make ToolSchema callable - delegates to the wrapped function."""
        return self.function(*args, **kwargs)

    def to_openrouter_format(self) -> dict[str, Any]:
        """Convert to OpenRouter function calling format.

        Returns:
            Dictionary compatible with OpenRouter's tools parameter
        """
        # Build JSON schema for parameters
        properties = {}
        required = []

        for param in self.parameters:
            properties[param.name] = {
                "type": param.type,
                "description": param.description
            }
            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }


def tool(func: Callable) -> ToolSchema:
    """Decorator to convert a function into a tool with schema.

    Inspired by LangChain's @tool decorator, but outputs OpenRouter-compatible schema.
    Automatically extracts schema from function signature and docstring.

    Args:
        func: Function to convert to a tool

    Returns:
        ToolSchema object with function and metadata

    Example:
        @tool
        def read_file(path: str) -> str:
            '''Read contents of a file.

            Args:
                path: Path to file to read
            '''
            return Path(path).read_text()
    """
    # Get function signature
    sig = inspect.signature(func)
    type_hints = get_type_hints(func)

    # Extract docstring
    doc = inspect.getdoc(func) or "No description"
    description = doc.split("\n\n")[0].strip()  # First paragraph

    # Parse parameters from docstring Args section
    param_descriptions = _parse_docstring_args(doc)

    # Build parameter list
    parameters = []
    for param_name, param in sig.parameters.items():
        # Skip internal parameters like _manager
        if param_name.startswith("_"):
            continue

        # Get type from annotation
        param_type = _python_type_to_json_type(type_hints.get(param_name, str))

        # Get description from docstring
        param_desc = param_descriptions.get(param_name, "No description")

        # Check if required (no default value)
        required = param.default == inspect.Parameter.empty

        parameters.append(ToolParameter(
            name=param_name,
            type=param_type,
            description=param_desc,
            required=required
        ))

    return ToolSchema(
        name=func.__name__,
        description=description,
        function=func,
        parameters=parameters
    )


def _parse_docstring_args(docstring: str) -> dict[str, str]:
    """Parse Args section from docstring.

    Args:
        docstring: Function docstring

    Returns:
        Dictionary mapping parameter names to descriptions
    """
    result = {}
    lines = docstring.split("\n")

    in_args = False
    current_param = None
    current_desc = []

    for line in lines:
        stripped = line.strip()

        if stripped == "Args:":
            in_args = True
            continue

        if in_args:
            # Check if we hit next section
            if stripped.endswith(":") and not stripped.startswith(" "):
                break

            # Check if this is a parameter line (starts with word:)
            if ":" in stripped and not stripped.startswith(" "):
                # Save previous parameter
                if current_param:
                    result[current_param] = " ".join(current_desc).strip()

                # Parse new parameter
                parts = stripped.split(":", 1)
                current_param = parts[0].strip()
                current_desc = [parts[1].strip()] if len(parts) > 1 else []
            elif current_param:
                # Continuation of previous description
                current_desc.append(stripped)

    # Save last parameter
    if current_param:
        result[current_param] = " ".join(current_desc).strip()

    return result


def _python_type_to_json_type(python_type: type) -> str:
    """Convert Python type to JSON schema type.

    Args:
        python_type: Python type annotation

    Returns:
        JSON schema type string
    """
    # Handle string representations
    if isinstance(python_type, str):
        python_type_lower = python_type.lower()
        if "str" in python_type_lower:
            return "string"
        if "int" in python_type_lower:
            return "integer"
        if "float" in python_type_lower:
            return "number"
        if "bool" in python_type_lower:
            return "boolean"
        if "list" in python_type_lower or "array" in python_type_lower:
            return "array"
        return "string"

    # Handle actual types
    type_map = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object"
    }

    return type_map.get(python_type, "string")

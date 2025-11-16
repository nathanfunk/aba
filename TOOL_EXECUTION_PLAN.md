# Tool Execution Implementation Plan

## Problem Statement

Currently, the agent-builder has tools available (`create_agent`, `list_agents`, etc.) but cannot actually execute them. The LLM knows about the tools but can only generate text responses, not perform actions.

**Current Flow:**
```
User: "List all agents"
  ↓
LLM (with tool descriptions in system prompt)
  ↓
Response: "I'll list the agents for you... [describes what it would do]"
```

**Desired Flow:**
```
User: "List all agents"
  ↓
LLM decides to use list_agents tool
  ↓
Runtime executes list_agents()
  ↓
Result returned to LLM
  ↓
Response: "Here are the available agents: ..."
```

## Solution Approaches

### Option 1: OpenRouter Function Calling (Recommended)

Use OpenRouter's function calling API (similar to OpenAI's).

**Pros:**
- Clean, standardized approach
- Model decides when to use tools
- Built-in support in many models
- Handles multiple tool calls in sequence

**Cons:**
- Requires models that support function calling
- More complex integration
- Need to convert tool registry to OpenAI function schema

**Implementation:**
```python
# Define tools in OpenAI function format
tools = [
    {
        "type": "function",
        "function": {
            "name": "list_agents",
            "description": "List all available agents",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_agent",
            "description": "Create a new agent",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Agent name"},
                    "description": {"type": "string"},
                    "capabilities": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["name", "description"]
            }
        }
    }
]

# Call LLM with tools
response = requests.post(
    url,
    json={
        "model": model,
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto"
    }
)

# Handle tool calls in response
if response.choices[0].message.tool_calls:
    for tool_call in response.choices[0].message.tool_calls:
        result = execute_tool(tool_call.function.name, tool_call.function.arguments)
        # Add result to messages and call LLM again
```

### Option 2: ReAct Pattern (Simple, Transparent)

Have the LLM output structured text with "Thought/Action/Observation" format.

**Pros:**
- Works with any LLM
- Transparent reasoning
- Easy to debug
- No special API support needed

**Cons:**
- Requires careful prompt engineering
- Parsing can be fragile
- Multiple LLM calls per user message

**Implementation:**
```python
# System prompt includes format instructions
"""
When you need to use a tool, respond in this format:

Thought: [your reasoning]
Action: tool_name(arg1="value1", arg2="value2")
Observation: [wait for result]

After seeing the observation, provide your final answer.
"""

# Runtime parses responses
def parse_react(response):
    if "Action:" in response:
        # Extract tool call
        action = extract_action(response)
        # Execute tool
        result = execute_tool(action)
        # Return to LLM with observation
        return continue_with_observation(result)
    else:
        # Final answer
        return response
```

### Option 3: Simple String Markers (Easiest to Start)

Look for special markers in LLM responses to trigger tool execution.

**Pros:**
- Very simple to implement
- Works with any LLM
- Easy to understand and debug

**Cons:**
- Less sophisticated
- LLM might not use markers consistently
- Harder to pass complex arguments

**Implementation:**
```python
# System prompt tells LLM to use markers
"""
When you need to use a tool, output:
[TOOL:tool_name:arg1=value1,arg2=value2]

Available tools:
- [TOOL:list_agents]
- [TOOL:create_agent:name=X,description=Y,capabilities=Z]
"""

# Runtime parses and executes
def execute_if_tool_call(response):
    if "[TOOL:" in response:
        tool_call = parse_tool_marker(response)
        result = execute_tool(tool_call)
        # Replace marker with result
        return response.replace(tool_call.marker, result)
    return response
```

## Recommended Approach: Function Calling

Start with OpenRouter function calling for best results, with fallback to ReAct pattern for models that don't support it.

## Implementation Steps

### Phase 1: Function Calling Infrastructure (4-6 hours)

**1. Create Tool Schema Generator**

File: `src/aba/tool_schemas.py`

```python
def tool_to_openai_schema(tool_name: str, tool_func) -> dict:
    """Convert tool function to OpenAI function schema."""
    # Parse docstring and signature
    # Return schema dict

def get_tools_schema(tools: dict) -> list:
    """Get OpenAI function schemas for all tools."""
    return [tool_to_openai_schema(name, func) for name, func in tools.items()]
```

**2. Update OpenRouterLanguageModel**

File: `src/aba/language_model.py`

```python
class OpenRouterLanguageModel:
    def complete_with_tools(
        self,
        messages: list[dict],
        tools: list[dict] = None
    ) -> dict:
        """Complete with optional tool calling support."""
        # Call OpenRouter API with tools parameter
        # Return full response including tool_calls
```

**3. Update AgentRuntime**

File: `src/aba/runtime.py`

```python
class AgentRuntime:
    def _generate_response_with_tools(self, user_input: str) -> str:
        """Generate response with tool execution support."""

        messages = self._build_messages()

        # Get tool schemas if agent has capabilities
        tool_schemas = None
        if self.tools:
            tool_schemas = get_tools_schema(self.tools)

        # Call LLM
        response = self.model.complete_with_tools(messages, tool_schemas)

        # Handle tool calls
        if response.get("tool_calls"):
            return self._execute_tool_calls(response, messages)

        return response["content"]

    def _execute_tool_calls(self, response, messages):
        """Execute tool calls and get final response."""
        for tool_call in response["tool_calls"]:
            # Execute tool
            result = self._execute_tool(
                tool_call["function"]["name"],
                tool_call["function"]["arguments"]
            )

            # Add to conversation
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": result
            })

        # Get final response from LLM
        final = self.model.complete_with_tools(messages, None)
        return final["content"]

    def _execute_tool(self, name: str, arguments: dict) -> str:
        """Execute a single tool and return result."""
        if name not in self.tools:
            return f"Error: Tool {name} not found"

        tool_func = self.tools[name]

        # Add _manager parameter for tools that need it
        if name in ["create_agent", "modify_agent", "delete_agent", "list_agents"]:
            arguments["_manager"] = self.manager

        try:
            result = tool_func(**arguments)
            return str(result)
        except Exception as e:
            return f"Error executing {name}: {e}"
```

### Phase 2: Tool Schema Definitions (2-3 hours)

Create schemas for each tool:

```python
TOOL_SCHEMAS = {
    "list_agents": {
        "name": "list_agents",
        "description": "List all available agents in the system",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    "create_agent": {
        "name": "create_agent",
        "description": "Create a new agent with specified capabilities",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Unique name for the agent (lowercase, hyphens allowed)"
                },
                "description": {
                    "type": "string",
                    "description": "Brief description of what the agent does"
                },
                "capabilities": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of capabilities to grant (agent-creation, file-operations, code-execution, web-access)",
                    "default": []
                },
                "system_prompt": {
                    "type": "string",
                    "description": "Custom system prompt for the agent",
                    "default": ""
                }
            },
            "required": ["name", "description"]
        }
    },
    # ... more tools
}
```

### Phase 3: Testing (2-3 hours)

**Unit Tests:**
- Test tool schema generation
- Test tool execution with mocked LLM responses
- Test error handling

**Integration Tests:**
- Test full conversation with tool calls
- Test multiple tool calls in sequence
- Test tool call with errors

**Manual Tests:**
- Ask agent-builder to list agents
- Ask agent-builder to create an agent
- Verify tools execute correctly

### Phase 4: Fallback Pattern (Optional, 2-3 hours)

For models that don't support function calling:

```python
class AgentRuntime:
    def _generate_response(self, user_input: str) -> str:
        # Try function calling first
        if self.model.supports_function_calling:
            return self._generate_response_with_tools(user_input)
        else:
            # Fall back to ReAct pattern
            return self._generate_response_react(user_input)
```

## Total Estimated Time

- Phase 1: 4-6 hours (core infrastructure)
- Phase 2: 2-3 hours (tool schemas)
- Phase 3: 2-3 hours (testing)
- Phase 4: 2-3 hours (fallback, optional)

**Total: 10-15 hours** for complete implementation

## Success Criteria

✅ Agent-builder can execute `list_agents` and see actual results
✅ Agent-builder can create new agents using `create_agent`
✅ Tool execution works with multiple tools in sequence
✅ Error handling works (tool not found, invalid args, etc.)
✅ Tests cover tool execution paths
✅ Documentation updated

## Alternative: Quick Prototype (2-3 hours)

For faster validation, implement Option 3 (Simple String Markers) first:

1. Update system prompt to include tool usage instructions
2. Parse responses for [TOOL:name:args] markers
3. Execute tools and replace markers with results
4. Test with agent-builder

This gives immediate functionality while we plan full function calling implementation.

## Next Steps

1. Decide on approach (function calling vs. simple markers)
2. Implement Phase 1 (core infrastructure)
3. Test with agent-builder listing agents
4. Expand to other tools
5. Add comprehensive tests
6. Update documentation

## Questions to Consider

1. Should tool execution be always-on or opt-in per agent?
2. How to handle tool execution failures gracefully?
3. Should we show tool execution to the user? ("Executing list_agents...")
4. Rate limiting for tool calls (prevent infinite loops)?
5. Should users be able to confirm tool execution? (security)

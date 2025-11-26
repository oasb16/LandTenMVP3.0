"""
Dynamic Tool Loader - Loads dynamic tools into the function registry at runtime.
Bridges dynamic tools with the existing function execution system.
"""
import logging
from typing import Dict, Any, List, Optional

from ..models.orchestrator_schemas import FunctionDefinition, FunctionResult
from .tool_runtime import get_dynamic_tool_runtime

logger = logging.getLogger(__name__)


class DynamicToolLoader:
    """
    Loads dynamic tools into the main function registry.
    Converts dynamic tools into FunctionDefinition format for orchestrator.
    """

    def __init__(self):
        self.runtime = get_dynamic_tool_runtime()

    def get_dynamic_function_definitions(self) -> List[FunctionDefinition]:
        """
        Get all dynamic tools as FunctionDefinition objects.
        These can be passed to the orchestrator alongside built-in functions.

        Returns:
            List of FunctionDefinition objects for all registered dynamic tools
        """
        tools = self.runtime.list_tools()
        function_defs = []

        for tool in tools:
            tool_name = tool["tool_name"]
            metadata = tool["metadata"]
            description = tool["description"]

            # Build parameter schema from function metadata
            properties = {}
            required = []

            for arg in metadata.get("args", []):
                arg_name = arg["name"]
                arg_type = arg.get("type", "string")

                # Convert Python type to JSON schema type
                json_type = self._python_type_to_json_schema(arg_type)

                properties[arg_name] = {
                    "type": json_type,
                    "description": f"Parameter {arg_name}",
                }

                # Mark all args as required (can be refined later)
                required.append(arg_name)

            parameters = {
                "type": "object",
                "properties": properties,
                "required": required,
            }

            function_def = FunctionDefinition(
                name=tool_name,
                description=f"[DYNAMIC TOOL] {description}",
                parameters=parameters,
            )

            function_defs.append(function_def)

        logger.info(f"📦 Loaded {len(function_defs)} dynamic tool definitions")
        return function_defs

    async def execute_dynamic_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> FunctionResult:
        """
        Execute a dynamic tool and return FunctionResult.
        This is called by the function registry's execute_function.

        Args:
            tool_name: Name of the dynamic tool
            arguments: Arguments to pass to the tool
            context: Execution context (user_id, channel_id, etc.)

        Returns:
            FunctionResult with success status and data
        """
        logger.info(f"🔧 Executing dynamic tool: {tool_name}")

        # Execute the tool through runtime
        result = self.runtime.execute_tool(tool_name, arguments)

        if result["success"]:
            return FunctionResult(
                success=True,
                data={
                    "tool_name": tool_name,
                    "result": result.get("result"),
                    "type": "dynamic_tool_execution",
                },
                message=f"Dynamic tool '{tool_name}' executed successfully",
            )
        else:
            return FunctionResult(
                success=False,
                error=result.get("error", "Unknown error"),
                message=f"Dynamic tool '{tool_name}' execution failed",
            )

    def _python_type_to_json_schema(self, python_type: Optional[str]) -> str:
        """Convert Python type annotation to JSON schema type"""
        if not python_type:
            return "string"

        type_mapping = {
            "str": "string",
            "int": "integer",
            "float": "number",
            "bool": "boolean",
            "list": "array",
            "dict": "object",
            "Dict": "object",
            "List": "array",
            "Optional": "string",  # Simplified
        }

        for py_type, json_type in type_mapping.items():
            if py_type in python_type:
                return json_type

        return "string"  # Default fallback


# Singleton instance
_dynamic_tool_loader = None


def get_dynamic_tool_loader() -> DynamicToolLoader:
    """Get singleton instance of DynamicToolLoader"""
    global _dynamic_tool_loader
    if _dynamic_tool_loader is None:
        _dynamic_tool_loader = DynamicToolLoader()
    return _dynamic_tool_loader

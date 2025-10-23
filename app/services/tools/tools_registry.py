"""
Tools Registry (Phase 5: Tool Ecosystem)
Central registry for managing and executing external tools
"""
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from app.utils.logger import get_logger
import asyncio

logger = get_logger(__name__)


class ToolCategory(str, Enum):
    """Categories of tools available"""
    COMMUNICATION = "communication"  # Email, SMS, messaging
    SCHEDULING = "scheduling"        # Calendar, appointments
    DATA = "data"                    # CRM, databases
    SEARCH = "search"                # Web search, knowledge lookup
    UTILITY = "utility"              # General utilities


class Tool:
    """Base tool class"""

    def __init__(
        self,
        name: str,
        description: str,
        category: ToolCategory,
        enabled: bool = True,
        requires_auth: bool = False
    ):
        self.name = name
        self.description = description
        self.category = category
        self.enabled = enabled
        self.requires_auth = requires_auth
        self.execution_count = 0
        self.success_count = 0
        self.failure_count = 0

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the tool with given parameters

        Args:
            params: Tool execution parameters

        Returns:
            Execution result
        """
        raise NotImplementedError("Tool must implement execute() method")

    def validate_params(self, params: Dict[str, Any]) -> bool:
        """
        Validate parameters before execution

        Args:
            params: Parameters to validate

        Returns:
            True if valid
        """
        return True

    def get_schema(self) -> Dict[str, Any]:
        """
        Get parameter schema for this tool

        Returns:
            JSON schema describing parameters
        """
        return {
            "type": "object",
            "properties": {},
            "required": []
        }

    def record_execution(self, success: bool):
        """Record execution statistics"""
        self.execution_count += 1
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get tool usage statistics"""
        success_rate = (self.success_count / self.execution_count * 100) if self.execution_count > 0 else 0

        return {
            "name": self.name,
            "executions": self.execution_count,
            "successes": self.success_count,
            "failures": self.failure_count,
            "success_rate": round(success_rate, 2),
            "enabled": self.enabled
        }


class ToolRegistry:
    """Central registry for all tools"""

    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        logger.info("Tool registry initialized")

    def register_tool(self, tool: Tool):
        """
        Register a new tool

        Args:
            tool: Tool instance to register
        """
        if tool.name in self.tools:
            logger.warning(f"Tool {tool.name} already registered, overwriting")

        self.tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name} ({tool.category.value})")

    def unregister_tool(self, tool_name: str) -> bool:
        """
        Unregister a tool

        Args:
            tool_name: Name of tool to remove

        Returns:
            True if removed successfully
        """
        if tool_name in self.tools:
            del self.tools[tool_name]
            logger.info(f"Unregistered tool: {tool_name}")
            return True
        else:
            logger.warning(f"Tool {tool_name} not found in registry")
            return False

    def get_tool(self, tool_name: str) -> Optional[Tool]:
        """
        Get tool by name

        Args:
            tool_name: Tool name

        Returns:
            Tool instance or None
        """
        return self.tools.get(tool_name)

    def list_tools(self, category: Optional[ToolCategory] = None, enabled_only: bool = True) -> List[Dict[str, Any]]:
        """
        List available tools

        Args:
            category: Optional category filter
            enabled_only: Only return enabled tools

        Returns:
            List of tool information
        """
        tools_list = []

        for tool in self.tools.values():
            # Apply filters
            if category and tool.category != category:
                continue

            if enabled_only and not tool.enabled:
                continue

            tools_list.append({
                "name": tool.name,
                "description": tool.description,
                "category": tool.category.value,
                "enabled": tool.enabled,
                "requires_auth": tool.requires_auth
            })

        return tools_list

    async def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool by name

        Args:
            tool_name: Name of tool to execute
            params: Execution parameters

        Returns:
            Execution result
        """
        logger.info(f"Executing tool: {tool_name}")

        tool = self.get_tool(tool_name)

        if not tool:
            logger.error(f"Tool not found: {tool_name}")
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not found in registry"
            }

        if not tool.enabled:
            logger.warning(f"Tool {tool_name} is disabled")
            return {
                "success": False,
                "error": f"Tool '{tool_name}' is currently disabled"
            }

        # Validate parameters
        if not tool.validate_params(params):
            logger.error(f"Invalid parameters for tool {tool_name}")
            return {
                "success": False,
                "error": f"Invalid parameters for tool '{tool_name}'"
            }

        # Execute tool
        try:
            result = await tool.execute(params)
            tool.record_execution(success=result.get("success", False))

            logger.info(f"Tool {tool_name} executed: {result.get('success', False)}")
            return result

        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            tool.record_execution(success=False)

            return {
                "success": False,
                "error": str(e),
                "tool": tool_name
            }

    async def execute_parallel(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Execute multiple tools in parallel

        Args:
            tool_calls: List of {tool_name, params} dicts

        Returns:
            List of results
        """
        logger.info(f"Executing {len(tool_calls)} tools in parallel")

        tasks = [
            self.execute_tool(call["tool_name"], call.get("params", {}))
            for call in tool_calls
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to error results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "success": False,
                    "error": str(result),
                    "tool": tool_calls[i]["tool_name"]
                })
            else:
                processed_results.append(result)

        return processed_results

    def get_all_stats(self) -> List[Dict[str, Any]]:
        """Get statistics for all tools"""
        return [tool.get_stats() for tool in self.tools.values()]

    def enable_tool(self, tool_name: str) -> bool:
        """Enable a tool"""
        tool = self.get_tool(tool_name)
        if tool:
            tool.enabled = True
            logger.info(f"Enabled tool: {tool_name}")
            return True
        return False

    def disable_tool(self, tool_name: str) -> bool:
        """Disable a tool"""
        tool = self.get_tool(tool_name)
        if tool:
            tool.enabled = False
            logger.info(f"Disabled tool: {tool_name}")
            return True
        return False


# Global registry instance
_registry = None


def get_tool_registry() -> ToolRegistry:
    """Get global tool registry instance (singleton)"""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
        # Auto-register tools on first access
        _initialize_tools(_registry)
    return _registry


def _initialize_tools(registry: ToolRegistry):
    """Initialize and register all available tools"""
    logger.info("Initializing tool ecosystem")

    # Import and register tools
    try:
        from app.services.tools.email_tool import EmailTool
        registry.register_tool(EmailTool())
    except Exception as e:
        logger.warning(f"Failed to register EmailTool: {e}")

    try:
        from app.services.tools.calendar_tool import CalendarTool
        registry.register_tool(CalendarTool())
    except Exception as e:
        logger.warning(f"Failed to register CalendarTool: {e}")

    try:
        from app.services.tools.web_search_tool import WebSearchTool
        registry.register_tool(WebSearchTool())
    except Exception as e:
        logger.warning(f"Failed to register WebSearchTool: {e}")

    try:
        from app.services.tools.crm_tool import CRMTool
        registry.register_tool(CRMTool())
    except Exception as e:
        logger.warning(f"Failed to register CRMTool: {e}")

    logger.info(f"Tool ecosystem initialized with {len(registry.tools)} tools")

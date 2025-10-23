"""
Tests for tools system (Phase 5: Tool Ecosystem)
"""
import pytest
from app.services.tools.tools_registry import Tool, ToolRegistry, ToolCategory, get_tool_registry
from app.services.tools.email_tool import EmailTool
from app.services.tools.calendar_tool import CalendarTool
from app.services.tools.web_search_tool import WebSearchTool
from app.services.tools.crm_tool import CRMTool


# ========================================
# Test Tool Registry
# ========================================

def test_tool_registry_singleton():
    """Test that registry is singleton"""
    registry1 = get_tool_registry()
    registry2 = get_tool_registry()

    assert registry1 is registry2


def test_tool_registry_initialization():
    """Test registry initializes with tools"""
    registry = get_tool_registry()

    # Should have tools registered
    assert len(registry.tools) > 0

    # Check expected tools
    tool_names = [tool.name for tool in registry.tools.values()]
    assert "send_email" in tool_names
    assert "calendar" in tool_names
    assert "web_search" in tool_names
    assert "crm" in tool_names


def test_get_tool():
    """Test getting tool by name"""
    registry = get_tool_registry()

    email_tool = registry.get_tool("send_email")
    assert email_tool is not None
    assert isinstance(email_tool, EmailTool)


def test_list_tools():
    """Test listing tools"""
    registry = get_tool_registry()

    all_tools = registry.list_tools(enabled_only=False)
    assert len(all_tools) >= 4  # At least 4 tools

    enabled_tools = registry.list_tools(enabled_only=True)
    assert all(tool["enabled"] for tool in enabled_tools)


def test_list_tools_by_category():
    """Test filtering tools by category"""
    registry = get_tool_registry()

    comm_tools = registry.list_tools(category=ToolCategory.COMMUNICATION)
    assert len(comm_tools) >= 1  # At least email tool

    search_tools = registry.list_tools(category=ToolCategory.SEARCH)
    assert len(search_tools) >= 1  # At least web search tool


def test_enable_disable_tool():
    """Test enabling/disabling tools"""
    registry = ToolRegistry()  # New instance for testing

    # Create test tool
    class TestTool(Tool):
        def __init__(self):
            super().__init__("test_tool", "Test", ToolCategory.UTILITY)

        async def execute(self, params):
            return {"success": True}

    test_tool = TestTool()
    registry.register_tool(test_tool)

    # Disable tool
    assert registry.disable_tool("test_tool") == True
    assert test_tool.enabled == False

    # Enable tool
    assert registry.enable_tool("test_tool") == True
    assert test_tool.enabled == True


# ========================================
# Test Email Tool
# ========================================

def test_email_tool_initialization():
    """Test email tool creation"""
    tool = EmailTool()

    assert tool.name == "send_email"
    assert tool.category == ToolCategory.COMMUNICATION
    assert tool.requires_auth == True


def test_email_tool_validate_params():
    """Test email parameter validation"""
    tool = EmailTool()

    # Valid params
    valid_params = {
        "to": "test@example.com",
        "subject": "Test Email",
        "body": "Test body"
    }
    assert tool.validate_params(valid_params) == True

    # Missing required field
    invalid_params = {
        "to": "test@example.com",
        "subject": "Test"
        # Missing body
    }
    assert tool.validate_params(invalid_params) == False

    # Invalid email format
    invalid_email = {
        "to": "invalid-email",
        "subject": "Test",
        "body": "Body"
    }
    assert tool.validate_params(invalid_email) == False


def test_email_tool_schema():
    """Test email tool schema"""
    tool = EmailTool()
    schema = tool.get_schema()

    assert "properties" in schema
    assert "to" in schema["properties"]
    assert "subject" in schema["properties"]
    assert "body" in schema["properties"]
    assert "to" in schema["required"]


@pytest.mark.asyncio
async def test_email_tool_execute_not_configured():
    """Test email execution when not configured"""
    tool = EmailTool()

    # Clear configuration
    tool.configured = False

    result = await tool.execute({
        "to": "test@example.com",
        "subject": "Test",
        "body": "Test body"
    })

    assert result["success"] == False
    assert "not configured" in result["error"].lower()


# ========================================
# Test Calendar Tool
# ========================================

def test_calendar_tool_initialization():
    """Test calendar tool creation"""
    tool = CalendarTool()

    assert tool.name == "calendar"
    assert tool.category == ToolCategory.SCHEDULING


def test_calendar_tool_validate_params():
    """Test calendar parameter validation"""
    tool = CalendarTool()

    # Valid check_availability
    valid_check = {
        "action": "check_availability",
        "date": "2025-01-15"
    }
    assert tool.validate_params(valid_check) == True

    # Valid schedule
    valid_schedule = {
        "action": "schedule",
        "date": "2025-01-15",
        "time": "10:00",
        "duration_minutes": 60,
        "description": "Meeting"
    }
    assert tool.validate_params(valid_schedule) == True

    # Invalid action
    invalid_action = {
        "action": "invalid_action"
    }
    assert tool.validate_params(invalid_action) == False

    # Missing required fields for schedule
    invalid_schedule = {
        "action": "schedule",
        "date": "2025-01-15"
        # Missing time, duration_minutes, description
    }
    assert tool.validate_params(invalid_schedule) == False


# ========================================
# Test Web Search Tool
# ========================================

def test_web_search_tool_initialization():
    """Test web search tool creation"""
    tool = WebSearchTool()

    assert tool.name == "web_search"
    assert tool.category == ToolCategory.SEARCH


def test_web_search_tool_validate_params():
    """Test web search parameter validation"""
    tool = WebSearchTool()

    # Valid params
    valid_params = {
        "query": "test search query"
    }
    assert tool.validate_params(valid_params) == True

    # Missing query
    invalid_params = {}
    assert tool.validate_params(invalid_params) == False

    # Empty query
    empty_query = {
        "query": "   "
    }
    assert tool.validate_params(empty_query) == False


@pytest.mark.asyncio
async def test_web_search_tool_execute():
    """Test web search execution"""
    tool = WebSearchTool()

    try:
        result = await tool.execute({
            "query": "test query",
            "num_results": 3
        })

        # Should return result structure even if search fails
        assert "success" in result
        assert "query" in result or "error" in result

    except Exception as e:
        # Network errors are acceptable in tests
        pytest.skip(f"Network not available: {e}")


# ========================================
# Test CRM Tool
# ========================================

def test_crm_tool_initialization():
    """Test CRM tool creation"""
    tool = CRMTool()

    assert tool.name == "crm"
    assert tool.category == ToolCategory.DATA


def test_crm_tool_validate_params():
    """Test CRM parameter validation"""
    tool = CRMTool()

    # Valid create_contact
    valid_create = {
        "action": "create_contact",
        "email": "test@example.com"
    }
    assert tool.validate_params(valid_create) == True

    # Valid get_contact
    valid_get = {
        "action": "get_contact",
        "email": "test@example.com"
    }
    assert tool.validate_params(valid_get) == True

    # Valid log_interaction
    valid_log = {
        "action": "log_interaction",
        "contact_id": "uuid",
        "interaction_type": "call",
        "notes": "Test notes"
    }
    assert tool.validate_params(valid_log) == True

    # Invalid action
    invalid_action = {
        "action": "invalid_action"
    }
    assert tool.validate_params(invalid_action) == False

    # Missing required fields
    invalid_create = {
        "action": "create_contact"
        # Missing email
    }
    assert tool.validate_params(invalid_create) == False


# ========================================
# Test Tool Execution via Registry
# ========================================

@pytest.mark.asyncio
async def test_execute_tool_via_registry():
    """Test executing tool through registry"""
    registry = ToolRegistry()

    # Register test tool
    class MockTool(Tool):
        def __init__(self):
            super().__init__("mock_tool", "Mock Tool", ToolCategory.UTILITY)

        async def execute(self, params):
            return {
                "success": True,
                "message": "Executed successfully",
                "params_received": params
            }

        def validate_params(self, params):
            return "test_param" in params

    registry.register_tool(MockTool())

    # Execute tool
    result = await registry.execute_tool("mock_tool", {"test_param": "value"})

    assert result["success"] == True
    assert "message" in result


@pytest.mark.asyncio
async def test_execute_tool_not_found():
    """Test executing non-existent tool"""
    registry = ToolRegistry()

    result = await registry.execute_tool("nonexistent_tool", {})

    assert result["success"] == False
    assert "not found" in result["error"].lower()


@pytest.mark.asyncio
async def test_execute_tool_disabled():
    """Test executing disabled tool"""
    registry = ToolRegistry()

    # Register and disable test tool
    class MockTool(Tool):
        def __init__(self):
            super().__init__("mock_tool", "Mock", ToolCategory.UTILITY, enabled=False)

        async def execute(self, params):
            return {"success": True}

    registry.register_tool(MockTool())

    result = await registry.execute_tool("mock_tool", {})

    assert result["success"] == False
    assert "disabled" in result["error"].lower()


@pytest.mark.asyncio
async def test_execute_tool_invalid_params():
    """Test executing tool with invalid params"""
    registry = ToolRegistry()

    # Register test tool with validation
    class MockTool(Tool):
        def __init__(self):
            super().__init__("mock_tool", "Mock", ToolCategory.UTILITY)

        async def execute(self, params):
            return {"success": True}

        def validate_params(self, params):
            return "required_field" in params

    registry.register_tool(MockTool())

    result = await registry.execute_tool("mock_tool", {})  # No required_field

    assert result["success"] == False
    assert "invalid parameters" in result["error"].lower()


# ========================================
# Test Parallel Execution
# ========================================

@pytest.mark.asyncio
async def test_execute_parallel():
    """Test parallel tool execution"""
    registry = ToolRegistry()

    # Register test tools
    class FastTool(Tool):
        def __init__(self):
            super().__init__("fast_tool", "Fast", ToolCategory.UTILITY)

        async def execute(self, params):
            return {"success": True, "result": "fast"}

    class SlowTool(Tool):
        def __init__(self):
            super().__init__("slow_tool", "Slow", ToolCategory.UTILITY)

        async def execute(self, params):
            import asyncio
            await asyncio.sleep(0.1)
            return {"success": True, "result": "slow"}

    registry.register_tool(FastTool())
    registry.register_tool(SlowTool())

    # Execute in parallel
    tool_calls = [
        {"tool_name": "fast_tool", "params": {}},
        {"tool_name": "slow_tool", "params": {}}
    ]

    results = await registry.execute_parallel(tool_calls)

    assert len(results) == 2
    assert results[0]["success"] == True
    assert results[1]["success"] == True


# ========================================
# Test Tool Statistics
# ========================================

@pytest.mark.asyncio
async def test_tool_statistics():
    """Test tool execution statistics"""
    registry = ToolRegistry()

    class TestTool(Tool):
        def __init__(self):
            super().__init__("test_tool", "Test", ToolCategory.UTILITY)
            self.call_count = 0

        async def execute(self, params):
            self.call_count += 1
            # Fail on second call
            if self.call_count == 2:
                return {"success": False, "error": "Intentional failure"}
            return {"success": True}

    tool = TestTool()
    registry.register_tool(tool)

    # Execute 3 times (2 success, 1 failure)
    await registry.execute_tool("test_tool", {})
    await registry.execute_tool("test_tool", {})
    await registry.execute_tool("test_tool", {})

    stats = tool.get_stats()

    assert stats["executions"] == 3
    assert stats["successes"] == 2
    assert stats["failures"] == 1
    assert stats["success_rate"] == pytest.approx(66.67, abs=0.1)


# ========================================
# Edge Cases
# ========================================

def test_register_duplicate_tool():
    """Test registering tool with duplicate name"""
    registry = ToolRegistry()

    class ToolA(Tool):
        def __init__(self):
            super().__init__("duplicate", "Tool A", ToolCategory.UTILITY)

        async def execute(self, params):
            return {"tool": "A"}

    class ToolB(Tool):
        def __init__(self):
            super().__init__("duplicate", "Tool B", ToolCategory.UTILITY)

        async def execute(self, params):
            return {"tool": "B"}

    registry.register_tool(ToolA())
    registry.register_tool(ToolB())  # Should overwrite

    tool = registry.get_tool("duplicate")
    assert tool.description == "Tool B"  # Should be the second one


def test_unregister_tool():
    """Test unregistering tool"""
    registry = ToolRegistry()

    class TestTool(Tool):
        def __init__(self):
            super().__init__("test_tool", "Test", ToolCategory.UTILITY)

        async def execute(self, params):
            return {"success": True}

    registry.register_tool(TestTool())

    # Tool should exist
    assert registry.get_tool("test_tool") is not None

    # Unregister
    assert registry.unregister_tool("test_tool") == True

    # Tool should not exist
    assert registry.get_tool("test_tool") is None

    # Unregister non-existent
    assert registry.unregister_tool("nonexistent") == False

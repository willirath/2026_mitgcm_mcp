"""Tests for src/fesom2/server.py — tool registration and names."""

from src.fesom2.server import mcp

EXPECTED_TOOLS = {
    # Code navigation
    "search_code_tool",
    "find_modules_tool",
    "find_subroutines_tool",
    "get_module_tool",
    "get_subroutine_tool",
    "get_source_tool",
    "get_callers_tool",
    "get_callees_tool",
    "get_module_uses_tool",
    "namelist_to_code_tool",
    # Documentation search
    "search_docs_tool",
    "get_doc_source_tool",
    "list_setups_tool",
    # Domain knowledge
    "translate_lab_params_tool",
    "check_scales_tool",
    "lookup_gotcha_tool",
    "suggest_experiment_config_tool",
    "get_namelist_structure_tool",
    # Workflow
    "get_workflow_tool",
}


def _registered_names() -> set[str]:
    return {t.name for t in mcp._tool_manager.list_tools()}


def test_tool_count():
    names = _registered_names()
    assert len(names) == len(EXPECTED_TOOLS), (
        f"Expected {len(EXPECTED_TOOLS)} tools, got {len(names)}.\n"
        f"Extra: {names - EXPECTED_TOOLS}\n"
        f"Missing: {EXPECTED_TOOLS - names}"
    )


def test_all_expected_tools_registered():
    names = _registered_names()
    missing = EXPECTED_TOOLS - names
    assert not missing, f"Missing tools: {missing}"


def test_no_unexpected_tools():
    names = _registered_names()
    extra = names - EXPECTED_TOOLS
    assert not extra, f"Unexpected tools registered: {extra}"


def test_server_name():
    assert mcp.name == "fesom2"


def test_all_tools_have_descriptions():
    for tool in mcp._tool_manager.list_tools():
        assert tool.description and tool.description.strip(), (
            f"Tool {tool.name!r} has an empty description"
        )

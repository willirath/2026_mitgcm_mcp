"""Unit tests for src/fesom2/domain/workflow.py."""

from src.fesom2.domain.workflow import get_workflow

KNOWN_TASKS = [
    "design_experiment",
    "debug_configuration",
    "understand_module",
    "explore_code",
]


def test_all_tasks_no_arg():
    """get_workflow() with no argument returns all tasks."""
    result = get_workflow()
    for task in KNOWN_TASKS:
        assert task in result


def test_single_task():
    """get_workflow(task) returns only that task."""
    result = get_workflow("design_experiment")
    assert "design_experiment" in result
    assert len(result) == 1


def test_unknown_task_returns_empty():
    """Unknown task returns empty dict."""
    assert get_workflow("nonexistent_task") == {}


def test_each_workflow_has_required_keys():
    """Every task workflow must have description, steps, notes."""
    for task, wf in get_workflow().items():
        if task == "meta":
            continue
        assert "description" in wf, f"{task} missing description"
        assert "steps" in wf, f"{task} missing steps"
        assert "notes" in wf, f"{task} missing notes"


def test_steps_are_nonempty_lists():
    """steps must be a non-empty list for every task workflow."""
    for task, wf in get_workflow().items():
        if task == "meta":
            continue
        assert isinstance(wf["steps"], list), f"{task} steps not a list"
        assert len(wf["steps"]) > 0, f"{task} steps is empty"


def test_each_step_has_tool_and_purpose():
    """Every step must have tool and purpose keys."""
    for task, wf in get_workflow().items():
        if task == "meta":
            continue
        for i, step in enumerate(wf["steps"]):
            assert "tool" in step, f"{task} step {i} missing tool"
            assert "purpose" in step, f"{task} step {i} missing purpose"


def test_case_and_whitespace_normalisation():
    """Task lookup normalises case and spaces."""
    result = get_workflow("Design Experiment")
    assert "design_experiment" in result


def test_meta_present_in_no_arg_return():
    """get_workflow() includes a 'meta' entry."""
    assert "meta" in get_workflow()


def test_meta_not_in_single_task_return():
    """get_workflow(task) never returns meta."""
    for task in KNOWN_TASKS:
        result = get_workflow(task)
        assert "meta" not in result


def test_meta_has_required_keys():
    """meta entry has description, agents_md_snippet, fallback_policy, gap_report_format."""
    meta = get_workflow()["meta"]
    for key in ("description", "agents_md_snippet", "fallback_policy", "gap_report_format"):
        assert key in meta, f"meta missing '{key}'"


def test_meta_fallback_policy_has_default():
    """fallback_policy has exactly one entry with default=True."""
    policy = get_workflow()["meta"]["fallback_policy"]
    assert isinstance(policy, list)
    assert len(policy) > 0
    defaults = [p for p in policy if p.get("default")]
    assert len(defaults) == 1, "fallback_policy must have exactly one default entry"


def test_meta_fallback_policy_entries_have_required_keys():
    """Every fallback_policy entry has situation, recommendation, command, note, default."""
    for i, entry in enumerate(get_workflow()["meta"]["fallback_policy"]):
        for key in ("situation", "recommendation", "command", "note", "default"):
            assert key in entry, f"fallback_policy[{i}] missing '{key}'"


def test_meta_agents_md_snippet_mentions_agents_md():
    """agents_md_snippet references AGENTS.md."""
    snippet = get_workflow()["meta"]["agents_md_snippet"]
    assert "AGENTS.md" in snippet


def test_workflow_tool_names_are_known():
    """Every non-None tool referenced in a workflow step must be in the MCP tool registry."""
    from tests.fesom2.test_server import EXPECTED_TOOLS
    for task, wf in get_workflow().items():
        if task == "meta":
            continue
        for step in wf["steps"]:
            if step["tool"] is not None:
                assert step["tool"] in EXPECTED_TOOLS, (
                    f"{task}: step tool '{step['tool']}' not in EXPECTED_TOOLS"
                )

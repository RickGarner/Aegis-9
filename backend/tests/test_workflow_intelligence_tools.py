import asyncio
import json
from pathlib import Path

import pytest

from app.security_control import SecurityControlPolicy
from app.workflow_agent_tools import WorkflowAgentToolError
from app.workflow_intelligence_tools import INTELLIGENCE_TOOLS, WorkflowIntelligenceToolContext


def make_context(tmp_path: Path) -> WorkflowIntelligenceToolContext:
    policy_path = tmp_path / "security.json"
    policy_path.write_text(json.dumps({"schema_version": 1, "global_kill_switch": False, "adapters": {"workflow-intelligence-tools": {"enabled": True, "mode": "read-only", "capabilities": [tool.name for tool in INTELLIGENCE_TOOLS]}}}), encoding="utf-8")
    return WorkflowIntelligenceToolContext(tmp_path / "sandbox", SecurityControlPolicy(policy_path))


def invoke(context: WorkflowIntelligenceToolContext, name: str, arguments: dict) -> dict:
    return json.loads(asyncio.run(context.invoke(name, arguments)))


def seed(context: WorkflowIntelligenceToolContext) -> None:
    (context._root / "Monitor.csproj").write_text("<Project />", encoding="utf-8")
    (context._root / "Monitor.cs").write_text("public class Monitor { public void Refresh() { Feed.Refresh(); } }", encoding="utf-8")
    tests = context._root / "Tests"
    tests.mkdir()
    (tests / "MonitorTests.cs").write_text("class MonitorTests { void Test() { new Monitor().Refresh(); } }", encoding="utf-8")


def test_catalog_has_ten_closed_read_only_schemas() -> None:
    assert len(INTELLIGENCE_TOOLS) == 10
    assert len({tool.name for tool in INTELLIGENCE_TOOLS}) == 10
    assert all(tool.parameters["type"] == "object" and tool.parameters["additionalProperties"] is False for tool in INTELLIGENCE_TOOLS)


def test_symbol_impact_definition_and_graph_tools(tmp_path: Path) -> None:
    context = make_context(tmp_path)
    seed(context)
    assert invoke(context, "findSymbolUsages", {"symbol": "Monitor"})["count"] == 2
    definitions = invoke(context, "getDefinitionsAndReferences", {"symbol": "Monitor"})
    assert definitions["definitions"] and definitions["references"]
    impact = invoke(context, "analyzeChangeImpact", {"query": "Monitor", "path": "Monitor.cs"})
    assert impact["relatedTests"] == ["Tests/MonitorTests.cs"]
    assert invoke(context, "getSymbolGraph", {"symbol": "Refresh"})["edges"]


def test_project_memory_planning_ownership_and_suggestions(tmp_path: Path) -> None:
    context = make_context(tmp_path)
    seed(context)
    ownership = invoke(context, "getBuildTestOwnership", {"filePath": "Monitor.cs"})
    assert ownership["owningProjects"] == ["Monitor.csproj"]
    assert invoke(context, "getProjectExecutionPlan", {"requestSummary": "Add refresh monitoring"})["requiresUserApprovalBeforeImplementation"] is True
    assert invoke(context, "getRepositoryMemory", {})["snapshotId"]
    assert invoke(context, "getProjectImprovementSuggestions", {"focus": "all"})["suggestions"]


def test_activation_and_budget_are_bounded_and_non_authorizing(tmp_path: Path) -> None:
    context = make_context(tmp_path)
    activated = invoke(context, "activateToolGroup", {"group": "git"})
    assert "grants no additional authority" in activated["note"]
    budget = invoke(context, "estimateContextBudget", {"prompt": "small", "contextLength": 16384})
    assert budget["fits"] is True
    with pytest.raises(WorkflowAgentToolError):
        invoke(context, "findSymbolUsages", {"symbol": "bad symbol;"})

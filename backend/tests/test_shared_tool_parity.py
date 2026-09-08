import json
from pathlib import Path

from app.workflow_agent_tools import WORKFLOW_AGENT_TOOLS
from app.workflow_implementation_tools import IMPLEMENTATION_TOOLS
from app.workflow_sandbox_files import SANDBOX_FILE_TOOLS
from app.workflow_repository_tools import REPOSITORY_TOOLS
from app.workflow_intelligence_tools import INTELLIGENCE_TOOLS
from app.workflow_extended_tools import EXTENDED_TOOLS
from app.workflow_mcp_tools import MCP_WORKFLOW_TOOLS


CONTRACT_PATH = Path(__file__).resolve().parents[2] / "docs" / "SHARED-TOOL-PARITY-CONTRACT.json"


def test_every_aegis_tool_is_classified_and_every_shared_tool_is_implemented() -> None:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    registered = {tool.name for tool in (*WORKFLOW_AGENT_TOOLS, *IMPLEMENTATION_TOOLS, *SANDBOX_FILE_TOOLS, *REPOSITORY_TOOLS, *INTELLIGENCE_TOOLS, *EXTENDED_TOOLS, *MCP_WORKFLOW_TOOLS)}
    shared = {item["aegis9"] for item in contract["shared"]}
    product_specific = {item["tool"] for item in contract["productSpecific"]["aegis9"]}
    assert shared <= registered
    assert registered <= shared | product_specific
    assert contract["policy"]["newPortableToolRequiresBothProducts"] is True


def test_parity_contract_matches_developer_studio_copy_when_present() -> None:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    sibling = Path(__file__).resolve().parents[3] / "Aegis-Developer-Studio" / "docs" / "project" / "SHARED-TOOL-PARITY-CONTRACT.json"
    if sibling.exists():
        assert json.loads(sibling.read_text(encoding="utf-8")) == contract

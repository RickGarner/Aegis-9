import json
from dataclasses import dataclass
from typing import Any

from app.security_control import SecurityControlError, SecurityControlPolicy
from app.storage import JarvisStore, Workflow


class WorkflowAgentToolError(RuntimeError):
    pass


@dataclass(frozen=True)
class WorkflowAgentTool:
    name: str
    description: str
    parameters: dict[str, Any]

    def as_openai_tool(self) -> dict[str, Any]:
        return {"type": "function", "function": {"name": self.name, "description": self.description, "parameters": self.parameters}}


WORKFLOW_AGENT_TOOLS = (
    WorkflowAgentTool("get_workflow_request", "Read the current workflow title, request, language, revision, and submitted clarification answers.", {"type": "object", "additionalProperties": False, "properties": {}}),
    WorkflowAgentTool("list_workflow_attachments", "List the file IDs attached to this workflow. Use read_workflow_attachment to retrieve relevant extracted text.", {"type": "object", "additionalProperties": False, "properties": {}}),
    WorkflowAgentTool("read_workflow_attachment", "Read a bounded section of extracted text from one file attached to this workflow.", {"type": "object", "additionalProperties": False, "properties": {"fileId": {"type": "integer", "minimum": 1}, "offset": {"type": "integer", "minimum": 0}, "maxChars": {"type": "integer", "minimum": 500, "maximum": 12000}}, "required": ["fileId"]}),
)


class WorkflowAgentToolContext:
    def __init__(self, store: JarvisStore, workflow: Workflow, security_policy: SecurityControlPolicy) -> None:
        self._store = store
        self._workflow = workflow
        self._security = security_policy

    @property
    def definitions(self) -> list[dict[str, Any]]:
        return [tool.as_openai_tool() for tool in WORKFLOW_AGENT_TOOLS]

    async def invoke(self, name: str, arguments: dict[str, Any]) -> str:
        try:
            self._security.require("workflow-design-tools", name, mutating=False)
        except SecurityControlError as error:
            raise WorkflowAgentToolError(str(error)) from error
        if name == "get_workflow_request":
            self._require_empty(arguments)
            return json.dumps({"title": self._workflow.title, "request": self._workflow.description, "language": self._workflow.language, "revision": self._workflow.revision, "clarificationAnswers": self._workflow.clarification_answers})
        if name == "list_workflow_attachments":
            self._require_empty(arguments)
            return json.dumps({"attachmentIds": self._workflow.attachment_ids, "count": len(self._workflow.attachment_ids)})
        if name == "read_workflow_attachment":
            return self._read_attachment(arguments)
        raise WorkflowAgentToolError(f"Unknown workflow design tool '{name}'; default-deny policy blocked it.")

    @staticmethod
    def _require_empty(arguments: dict[str, Any]) -> None:
        if arguments:
            raise WorkflowAgentToolError("This workflow tool does not accept arguments.")

    def _read_attachment(self, arguments: dict[str, Any]) -> str:
        file_id = arguments.get("fileId")
        offset = arguments.get("offset", 0)
        max_chars = arguments.get("maxChars", 6000)
        if not isinstance(file_id, int) or isinstance(file_id, bool) or file_id not in self._workflow.attachment_ids:
            raise WorkflowAgentToolError("The requested file is not attached to this workflow.")
        if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
            raise WorkflowAgentToolError("offset must be a non-negative integer.")
        if not isinstance(max_chars, int) or isinstance(max_chars, bool) or not 500 <= max_chars <= 12000:
            raise WorkflowAgentToolError("maxChars must be between 500 and 12000.")
        content = self._store.get_file_content(file_id)
        if not content:
            raise WorkflowAgentToolError("No extracted text is available for the attached file.")
        section = content[offset:offset + max_chars]
        return json.dumps({"fileId": file_id, "offset": offset, "returnedChars": len(section), "hasMore": offset + len(section) < len(content), "content": section})

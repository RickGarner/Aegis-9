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
    WorkflowAgentTool("askQuestions", "Register up to five material questions for the existing user review gate. This tool never supplies or invents answers.", {"type": "object", "additionalProperties": False, "properties": {"questions": {"type": "array", "minItems": 1, "maxItems": 5, "items": {"type": "object", "additionalProperties": False, "properties": {"id": {"type": "string", "maxLength": 100}, "prompt": {"type": "string", "maxLength": 1000}, "required": {"type": "boolean"}, "options": {"type": "array", "maxItems": 10, "items": {"type": "string", "maxLength": 500}}}, "required": ["id", "prompt"]}}}, "required": ["questions"]}),
    WorkflowAgentTool("getRequestExecutionState", "Read the current workflow phase, revision, approval stage, and scheduler/test status without changing it.", {"type": "object", "additionalProperties": False, "properties": {}}),
    WorkflowAgentTool("getCompletionCriteria", "Evaluate the workflow's deterministic approval and evidence gates. This cannot approve or promote a workflow.", {"type": "object", "additionalProperties": False, "properties": {}}),
    WorkflowAgentTool("getValidationEvidence", "Read bounded retained non-production test status, summary, and evidence hash without returning raw secret-bearing output.", {"type": "object", "additionalProperties": False, "properties": {}}),
    WorkflowAgentTool("getArtifactManifest", "Read the workflow implementation artifact identity and permission manifest without returning executable content.", {"type": "object", "additionalProperties": False, "properties": {}}),
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
        if name == "askQuestions":
            return self._ask_questions(arguments)
        if name == "getRequestExecutionState":
            self._require_empty(arguments)
            return json.dumps({
                "workflowId": self._workflow.id,
                "revision": self._workflow.revision,
                "state": self._workflow.state,
                "approvalStage": self._workflow.approval_stage,
                "schedulerStatus": self._workflow.scheduler_status,
                "latestTestStatus": self._workflow.latest_test_status,
            })
        if name == "getCompletionCriteria":
            self._require_empty(arguments)
            return json.dumps(self._completion_criteria())
        if name == "getValidationEvidence":
            self._require_empty(arguments)
            return json.dumps({
                "status": self._workflow.latest_test_status,
                "summary": self._workflow.latest_test_summary[:4000],
                "evidenceSha256": self._workflow.latest_test_evidence_sha256,
                "retained": bool(self._workflow.latest_test_evidence_sha256),
            })
        if name == "getArtifactManifest":
            self._require_empty(arguments)
            return json.dumps({
                "workflowId": self._workflow.id,
                "revision": self._workflow.revision,
                "language": self._workflow.language,
                "artifactSha256": self._workflow.artifact_sha256,
                "implementationProvider": self._workflow.implementation_provider,
                "implementationModel": self._workflow.implementation_model,
                "permissionManifest": self._workflow.permission_manifest,
                "executableContentIncluded": False,
            })
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

    def _ask_questions(self, arguments: dict[str, Any]) -> str:
        questions = arguments.get("questions")
        if not isinstance(questions, list) or not 1 <= len(questions) <= 5:
            raise WorkflowAgentToolError("askQuestions requires between one and five questions.")
        normalized: list[dict[str, Any]] = []
        seen: set[str] = set()
        for question in questions:
            if not isinstance(question, dict):
                raise WorkflowAgentToolError("Each question must be an object.")
            question_id = question.get("id")
            prompt = question.get("prompt")
            if not isinstance(question_id, str) or not question_id.strip() or len(question_id) > 100 or question_id in seen:
                raise WorkflowAgentToolError("Each question requires a unique id of at most 100 characters.")
            if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 1000:
                raise WorkflowAgentToolError("Each question requires a prompt of at most 1000 characters.")
            options = question.get("options", [])
            if not isinstance(options, list) or len(options) > 10 or any(not isinstance(option, str) or not option.strip() or len(option) > 500 for option in options):
                raise WorkflowAgentToolError("Question options must contain at most ten non-empty strings.")
            seen.add(question_id)
            normalized.append({"id": question_id, "prompt": prompt, "required": question.get("required", True) is not False, "options": options})
        return json.dumps({"requiresUserReview": True, "questions": normalized, "submittedAnswers": {key: value for key, value in self._workflow.clarification_answers.items() if key in seen}})

    def _completion_criteria(self) -> dict[str, Any]:
        required_questions = [question.get("id") for question in self._workflow.clarification_questions if question.get("required", True)]
        unanswered = [question_id for question_id in required_questions if question_id and not self._workflow.clarification_answers.get(question_id)]
        criteria = {
            "requiredQuestionsAnswered": not unanswered,
            "planApproved": self._workflow.state not in {"draft", "design_review", "plan_review", "rejected"} and bool(self._workflow.plan_text),
            "testPlansApproved": self._workflow.state not in {"draft", "design_review", "plan_review", "rejected", "plan_approved", "test_plan_review"} and bool(self._workflow.test_plan_text),
            "implementationPresent": bool(self._workflow.artifact_sha256),
            "nonProductionTestsPassed": self._workflow.latest_test_status == "passed" and bool(self._workflow.latest_test_evidence_sha256),
            "userAcceptedResults": self._workflow.state in {"awaiting_supervisor", "approved", "scheduled", "active"},
            "supervisorApproved": bool(self._workflow.supervisor_approved_by and self._workflow.supervisor_approved_at),
        }
        return {"complete": all(criteria.values()), "criteria": criteria, "unansweredQuestionIds": unanswered, "productionActionAvailable": all(criteria.values())}

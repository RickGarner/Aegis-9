from __future__ import annotations

import getpass
import csv
import io
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


ROLES = frozenset({
    "Operator", "WorkflowDesigner", "WorkflowApprover", "Supervisor",
    "MonitoringAdministrator", "SecurityAuditor", "PlatformAdministrator",
})

CAPABILITIES = {
    "monitoring.read": {"Operator", "MonitoringAdministrator", "SecurityAuditor", "PlatformAdministrator"},
    "monitoring.configure": {"MonitoringAdministrator", "PlatformAdministrator"},
    "monitoring.acknowledge": {"Operator", "MonitoringAdministrator", "PlatformAdministrator"},
    "credentials.manage": {"PlatformAdministrator"},
    "workflow.read": {"Operator", "WorkflowDesigner", "WorkflowApprover", "Supervisor", "SecurityAuditor", "PlatformAdministrator"},
    "workflow.design": {"WorkflowDesigner", "PlatformAdministrator"},
    "workflow.approve": {"WorkflowApprover", "PlatformAdministrator"},
    "workflow.supervisor-approve": {"Supervisor", "PlatformAdministrator"},
    "workflow.execute": {"Operator", "Supervisor", "PlatformAdministrator"},
    "audit.read": {"SecurityAuditor", "PlatformAdministrator"},
    "security.configure": {"PlatformAdministrator"},
}


class AuthorizationError(PermissionError):
    pass


@dataclass(frozen=True)
class WindowsPrincipal:
    identity: str
    groups: frozenset[str] = frozenset()


class RoleAuthorizer:
    def __init__(self, policy_path: Path) -> None:
        self.policy_path = policy_path

    def current_principal(self) -> WindowsPrincipal:
        username = getpass.getuser()
        domain = os.environ.get("USERDOMAIN", "").strip()
        groups: set[str] = set()
        if os.name == "nt":
            try:
                result = subprocess.run(
                    ["whoami.exe", "/groups", "/fo", "csv", "/nh"],
                    capture_output=True, text=True, timeout=5,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), check=False,
                )
                if result.returncode == 0:
                    groups = {row[0].strip() for row in csv.reader(io.StringIO(result.stdout)) if row and row[0].strip()}
            except (OSError, subprocess.SubprocessError):
                groups = set()
        return WindowsPrincipal(f"{domain}\\{username}" if domain else username, frozenset(groups))

    def roles_for(self, principal: WindowsPrincipal) -> frozenset[str]:
        policy = self._load()
        roles: set[str] = set()
        identity = principal.identity.casefold()
        groups = {group.casefold() for group in principal.groups}
        for assignment in policy["assignments"]:
            subject = assignment["subject"].strip().casefold()
            if (assignment["type"] == "user" and subject == identity) or (assignment["type"] == "group" and subject in groups):
                roles.update(assignment["roles"])
        return frozenset(roles)

    def require(self, capability: str, principal: WindowsPrincipal | None = None) -> frozenset[str]:
        allowed = CAPABILITIES.get(capability)
        if allowed is None:
            raise AuthorizationError("Unknown capability was denied by default.")
        principal = principal or self.current_principal()
        roles = self.roles_for(principal)
        if roles.isdisjoint(allowed):
            raise AuthorizationError(f"Windows identity '{principal.identity}' is not authorized for '{capability}'.")
        return roles

    def _load(self) -> dict:
        try:
            policy = json.loads(self.policy_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise AuthorizationError(f"Role policy is unavailable or invalid: {error}") from error
        if not isinstance(policy, dict) or policy.get("schemaVersion") != 1 or not isinstance(policy.get("assignments"), list):
            raise AuthorizationError("Role policy schema is invalid.")
        for item in policy["assignments"]:
            if not isinstance(item, dict) or set(item) != {"type", "subject", "roles"} or item["type"] not in {"user", "group"}:
                raise AuthorizationError("Role assignment is invalid.")
            if (
                not isinstance(item["subject"], str)
                or not item["subject"].strip()
                or not isinstance(item["roles"], list)
                or not item["roles"]
                or any(not isinstance(role, str) or role not in ROLES for role in item["roles"])
                or len(item["roles"]) != len(set(item["roles"]))
            ):
                raise AuthorizationError("Role assignment contains an invalid subject or role.")
        return policy

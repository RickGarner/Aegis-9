# A.E.G.I.S.-9 authorization

Backend authorization is based on the current Windows identity and exact user or
Windows-group assignments in `config/role-mappings.json`. The initial deployment
uses `BSOC\BSOC - G - Architecture` as a temporary `PlatformAdministrator`
bootstrap assignment. Replace this broad mapping with separate least-privilege
groups before production acceptance.

Supported roles are Operator, WorkflowDesigner, WorkflowApprover, Supervisor,
MonitoringAdministrator, SecurityAuditor, and PlatformAdministrator. Role names
do not imply authority outside the capability map in `backend/app/authorization.py`.

Backend enforcement now covers the monitoring and workflow HTTP APIs as well as
protected-credential administration. UI visibility is not an authorization
control. Health/startup endpoints remain available so the governed startup gate
can diagnose an authorization failure.

| Capability | Permitted roles |
|---|---|
| `monitoring.read` | Operator, MonitoringAdministrator, SecurityAuditor, PlatformAdministrator |
| `monitoring.acknowledge` | Operator, MonitoringAdministrator, PlatformAdministrator |
| `monitoring.configure` | MonitoringAdministrator, PlatformAdministrator |
| `workflow.read` | Operator, WorkflowDesigner, WorkflowApprover, Supervisor, SecurityAuditor, PlatformAdministrator |
| `workflow.design` | WorkflowDesigner, PlatformAdministrator |
| `workflow.approve` | WorkflowApprover, PlatformAdministrator |
| `workflow.supervisor-approve` | Supervisor, PlatformAdministrator |
| `workflow.execute` | Operator, Supervisor, PlatformAdministrator |
| `credentials.manage` | PlatformAdministrator |

Workflow review authorization is decision-specific. A designer may submit an
implementation for testing, an approver controls plan/test-plan/user acceptance
gates, and a supervisor controls final production approval. The backend records
the qualified domain identity on production approval.

Example deployment assignment:

```json
{"type":"group","subject":"DOMAIN\\Aegis Supervisors","roles":["Supervisor"]}
```

Use exact domain-qualified names. Changes to production mappings require a
separate administrative approval, retained audit evidence, and restart until a
governed policy-management interface is accepted.

## Temporary bootstrap mapping

The Architecture group currently receives every capability represented by
`PlatformAdministrator`, including monitoring configuration, protected
credential management, workflow design and approval, supervisor approval,
audit review, and security configuration. This supports initial integration
work but is not the final production authorization design.

Authorization of the remaining non-workflow mutation APIs and a governed policy
administration surface remain release work. The current JSON mapping must be
changed only through an approved, audited deployment process.

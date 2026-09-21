# A.E.G.I.S.-9 authorization

Backend authorization is based on the current Windows identity and exact user or
Windows-group assignments in `config/role-mappings.json`. The initial deployment
uses `BSOC\BSOC - G - Architecture` as a temporary `PlatformAdministrator`
bootstrap assignment. Replace this broad mapping with separate least-privilege
groups before production acceptance.

Supported roles are Operator, WorkflowDesigner, WorkflowApprover, Supervisor,
MonitoringAdministrator, SecurityAuditor, and PlatformAdministrator. Role names
do not imply authority outside the capability map in `backend/app/authorization.py`.

The first enforced production boundary is `workflow.supervisor-approve`, which
requires Supervisor or PlatformAdministrator. The backend records the qualified
domain identity on the approval. UI visibility is not an authorization control.

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

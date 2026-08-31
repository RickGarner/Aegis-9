# Portable workflow transfer

A.E.G.I.S.-9 keeps operational state in each computer's local, git-ignored
SQLite database. Use Workflow Center export/import to move a workflow without
copying the complete database or exposing unrelated chat and monitoring state.

## Export

1. Locate the workflow under **Recently Active** or **Awaiting Action**.
2. Select **EXPORT**.
3. Save the generated `.aegisworkflow` file to an approved transfer location.

The versioned JSON package contains the workflow's stable transfer identity,
revision and lifecycle state, description, plans, generated implementation,
clarification questions and answers, schedule, related audit entries, and the
extracted text/metadata for referenced attachments. It does not contain provider
credentials, `.env`, chat history, monitoring data, or machine-specific paths.

## Import

1. Copy the `.aegisworkflow` file to the destination computer.
2. Select **IMPORT** in Workflow Center.
3. Review the imported state and revision shown by A.E.G.I.S.-9.

The first import creates a new local numeric ID while retaining the workflow's
stable transfer identity. Later packages update that same workflow only when the
incoming revision/timestamp is newer. Equal or older packages leave local work
unchanged. A workflow exported while running, queued, or paused imports as
paused with no monitor assignment; an operator must explicitly resume it.

Treat transfer files as operational data. They can include workflow-generated
code and extracted business-document text and should not be committed to Git or
placed in an unapproved shared folder.

## Multi-computer practice

- Export after completing workflow planning, answers, approval, or schedule
  changes on one computer.
- Import on the next computer before continuing that workflow.
- Export again before moving development back to another computer.
- Keep the source package until the destination confirms the expected title,
  revision, state, questions, answers, and plan.

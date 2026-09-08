# Technical basis used by this bundle

The bundle intentionally uses a narrow set of assumptions.

## Vendor-documented basis

Xerox FreeFlow Core Help documents the JMF Gateway as follows:

- JMF client connects to `http://hostname:7751/`.
- `KnownDevices` is used to retrieve workflows and queues.
- `SubmitQueueEntry` is used for job submission.
- `http://<Hostname>:7751/FreeFlowCore` is also a valid JMF client connection.
- Xerox states that supported JMF commands, signals, and JDF attributes are documented in the FreeFlow Core SDK.

Because the complete SDK command set is version-specific, the initial bundle enables only read-only discovery by default.

## Deliberately provisional area

The generated backend contains a feature-flagged JMF `Status` query using `StatusQuParams QueueInfo="true"` as a candidate path for job enumeration. It is disabled by default and must be validated against the installed FreeFlow Core SDK/version before use.

## Deliberately excluded from v1

- JMF mutation commands.
- Job submission.
- Printer IPP/SNMP.
- CoreReports automation.
- Windows server health.
- SQL health.
- Direct database access.

Those can be layered into the same AEGIS integration after the foundation is verified.

## Public Xerox reference used during design

Xerox FreeFlow Core Help (JMF Gateway section):

https://download.support.xerox.com/pub/docs/FF_CORE/userdocs/any-os/en_GB/Xerox_FreeFlow_Core_Help_en-US.pdf

The public help points developers to the FreeFlow Core SDK for the complete
supported JMF command/signal/JDF attribute matrix. Codex should validate the
installed FreeFlow Core release against that SDK before extending the connector.

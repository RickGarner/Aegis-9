# Startup and desktop acceptance — 2026-09-13

## Result

The native WPF release build succeeds and starts at the Guardian Boot Chamber.
With a separately verified healthy local backend, the splash requests and
receives successful health, provider, policy-integrity, and system-health
responses. A launch without a reachable backend remains on the halted splash
instead of entering the command center.

This is a partial desktop acceptance, not a production-ready declaration. The
current computer-control session returned no native application surfaces even
though Windows reported a responsive A.E.G.I.S. splash window. Consequently,
the four operator button paths could not be visually clicked and verified:

- Continue after all required gates pass.
- Continue Degraded after a required gate fails.
- Generate Diagnostic after a required gate fails.
- Close A.E.G.I.S. after a required gate fails.

Existing sanitized diagnostic artifacts under `%LOCALAPPDATA%\Aegis-9\logs`
confirm the diagnostic writer has executed. Final UI acceptance must still
confirm the visible confirmation text and the resulting navigation/termination
for each button.

## Evidence

- `dotnet build desktop/Aegis.Desktop/Aegis.Desktop.csproj -c Release`
  completed with zero errors. One existing unused-event warning was emitted
  twice by the WPF temporary and final projects.
- Windows reported a responsive process whose main-window title was
  `A.E.G.I.S.-9 · Guardian Boot Chamber`.
- The healthy-backend launch produced HTTP 200 requests for `/health`,
  `/api/provider/health`, `/api/security/policy-status`, and
  `/api/system/health` in the local backend log.
- The provider response reported an available local DMR route, policy status
  reported healthy with no drift, and system health remained non-critical when
  optional components were unavailable.
- A launch with no reachable backend stayed in the Guardian Boot Chamber and
  did not expose the main command center.

## Deferred items

The splash avatar is still pending by operator decision and must not be counted
as accepted. Reboot/service recovery, live microphone transcription, Kokoro
playback/interruption, and avatar speech synchronization also remain separate
manual/environment acceptance work.

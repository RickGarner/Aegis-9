# A.E.G.I.S.-9 Local-Only Mode

**Status:** Implemented  
**Products:** A.E.G.I.S.-9 and Aegis Developer Studio  
**Mode:** Local/offline by default  
**Last Updated:** 2026-09-21

## Overview

Local-Only Mode provides a fail-closed network policy that restricts all AI provider connections to local and approved private network endpoints. This mode is essential for air-gapped environments, classified networks, and scenarios where external network egress must be completely blocked.

## Security Model

### Fail-Closed Design

Local-Only Mode operates on a fail-closed principle:
- **Unknown endpoints are denied by default**
- **Cloud endpoints are explicitly blocked**
- **Only local and approved private hosts are allowed**
- **Network validation occurs before any connection attempt**

### Enforced Restrictions

| Restriction | Value | Purpose |
|-------------|-------|---------|
| Cloud Endpoints | Blocked | Prevents connection to public AI providers |
| Public IPs | Blocked | Prevents accidental egress to internet |
| Non-HTTP Protocols | Blocked | Only HTTP/HTTPS allowed |
| Unapproved Hosts | Blocked | Only localhost and approved private hosts |
| Credentials in Transit | Redacted | Secrets never sent to external endpoints |

## Configuration

### Backend Configuration

Enable Local-Only Mode via environment variable:

```bash
JARVIS_LOCAL_ONLY_MODE=true
```

Or in `.env` file:

```
JARVIS_LOCAL_ONLY_MODE=true
```

### Desktop Configuration

Enable in `appsettings.json`:

```json
{
  "localOnly": {
    "enabled": true,
    "allowPrivateNetwork": true,
    "allowedHosts": ["127.0.0.1", "localhost", "10.30.75.229"]
  }
}
```

Or via UserPreferences.cs:

```csharp
public bool LocalOnlyMode { get; set; } = false;
```

### Policy Configuration

The network policy can be configured with:

- `local_only_mode`: Enable/disable Local-Only Mode (default: false)
- `allow_private_network`: Allow private IP ranges (default: true)
- `allowed_hosts`: Explicit list of allowed hosts (default: ["127.0.0.1", "localhost"])

## Blocked Cloud Endpoints

The following cloud endpoints are automatically blocked in Local-Only Mode:

- `api.openai.com` and subdomains
- `api.anthropic.com` and subdomains
- `api.cohere.ai`
- `api.mistral.ai`
- `api.groq.com`
- `*.azure.com`
- `*.amazonaws.com`
- `*.googleapis.com`
- `*.microsoft.com`
- `copilot.microsoft.com`
- `api.github.com`

## Allowed Endpoints

### Local Endpoints (Always Allowed)

- `http://127.0.0.1:*` - Loopback addresses
- `http://localhost:*` - Localhost hostname

### Private Network Endpoints (When Enabled)

- `10.0.0.0/8` - Private Class A
- `172.16.0.0/12` - Private Class B
- `192.168.0.0/16` - Private Class C
- `169.254.0.0/16` - Link-local

### Custom Allowed Hosts

Add specific hosts to the allowlist:

```python
from app.network_policy import set_local_only_policy

set_local_only_policy(
    local_only_mode=True,
    allow_private_network=True,
    allowed_hosts=["127.0.0.1", "10.30.75.229", "internal.company.local"],
)
```

## API Endpoints

### Get Local-Only Status

```http
GET /api/local-only/status
```

**Response:**
```json
{
  "enabled": true,
  "policy": {
    "localOnlyMode": true,
    "allowPrivateNetwork": true,
    "allowedHosts": ["127.0.0.1", "localhost", "10.30.75.229"],
    "cloudEndpointsBlocked": 12
  }
}
```

### Enable Local-Only Mode

```http
POST /api/local-only/enable
```

**Response:**
```json
{
  "enabled": true,
  "policy": { ... }
}
```

### Disable Local-Only Mode

```http
POST /api/local-only/disable
```

**Response:**
```json
{
  "enabled": false,
  "policy": {
    "localOnlyMode": false,
    "allowPrivateNetwork": true,
    "allowedHosts": [],
    "cloudEndpointsBlocked": 12
  }
}
```

### Validate URL

```http
POST /api/local-only/validate-url?url=https://api.openai.com/v1/chat
```

**Response (blocked):**
```json
{
  "valid": false,
  "error": "Cloud endpoint blocked in Local-Only Mode"
}
```

**Response (allowed):**
```json
{
  "valid": true,
  "result": {
    "valid": true,
    "blocked": false,
    "reason": null
  }
}
```

## Provider Discovery Integration

Local-Only Mode is integrated into the provider discovery system:

1. **URL Validation**: All provider URLs are validated against the policy before connection
2. **Cloud Filtering**: Cloud endpoints are silently filtered during discovery
3. **Fail-Closed**: If no valid local providers are found, discovery returns empty results

### Example: Provider Discovery in Local-Only Mode

```python
# With Local-Only Mode enabled:
# - api.openai.com endpoints are blocked
# - 127.0.0.1:11434 (Ollama) is allowed
# - 10.30.75.229:12434 (DMR) is allowed

# Discovery will only return local/private providers
```

## Usage Scenarios

### Scenario 1: Air-Gapped Development

```bash
# Set environment variable
export JARVIS_LOCAL_ONLY_MODE=true

# Only local providers will be available
# Ollama on localhost:11434
# DMR on internal network:10.30.75.229:12434
```

### Scenario 2: Classified Network

```json
{
  "localOnly": {
    "enabled": true,
    "allowPrivateNetwork": true,
    "allowedHosts": ["127.0.0.1", "10.30.75.229", "192.168.1.100"]
  }
}
```

### Scenario 3: Secure Development Environment

```python
from app.network_policy import set_local_only_policy

# Configure for secure development
set_local_only_policy(
    local_only_mode=True,
    allow_private_network=True,
    allowed_hosts=[
        "127.0.0.1",
        "localhost",
        "10.30.75.229",  # Internal DMR
        "192.168.1.100",  # Internal Ollama
    ],
)
```

## Testing

### Unit Tests

Run the Local-Only Mode test suite:

```bash
cd backend
uv run pytest tests/test_local_only_mode.py -v
```

**Test Coverage:**
- Policy defaults and configuration
- Cloud endpoint detection
- URL validation (allow/block)
- Private IP handling
- Custom host allowlists
- Integration with provider discovery

### Acceptance Testing

To prove Local-Only Mode works with firewall blocked:

1. **Configure firewall** to block all outbound connections except localhost
2. **Enable Local-Only Mode** via environment variable
3. **Attempt to connect** to cloud endpoints (should fail)
4. **Verify local providers** still work (Ollama, DMR)
5. **Capture evidence** of blocked vs allowed connections

## Implementation Files

### Backend

- `backend/app/network_policy.py` - Network policy enforcement
- `backend/app/providers.py` - Provider discovery integration
- `backend/app/main.py` - API endpoints
- `backend/app/config.py` - Configuration settings
- `backend/tests/test_local_only_mode.py` - Unit tests

### Desktop

- `desktop/Aegis.Desktop/UserPreferences.cs` - User preferences
- `desktop/Aegis.Desktop/appsettings.json` - Configuration file

## Security Considerations

### Threat Model

Local-Only Mode protects against:
- **Accidental cloud egress**: Prevents misconfiguration from sending data to cloud
- **Malicious endpoint injection**: Blocks attempts to redirect to malicious servers
- **Data exfiltration**: Prevents sensitive data from leaving the local network
- **Credential theft**: Credentials never sent to unapproved endpoints

### Limitations

Local-Only Mode does NOT protect against:
- **Local malware**: Malicious code running on the local system
- **Compromised local providers**: If a local provider is compromised
- **Physical access attacks**: Someone with physical access to the machine
- **Supply chain attacks**: Compromised dependencies or updates

### Recommendations

1. **Regular audits**: Periodically review the allowed hosts list
2. **Network monitoring**: Use firewall logs to verify no egress occurs
3. **Provider verification**: Ensure local providers are trusted
4. **Incident response**: Have a plan for detecting policy violations

## Future Enhancements

- [ ] DNS-based egress filtering
- [ ] Certificate pinning for local providers
- [ ] Automated policy violation detection
- [ ] Integration with Windows Firewall API
- [ ] Real-time egress monitoring dashboard
- [ ] Policy violation audit logging
- [ ] Dynamic policy updates without restart

## References

- [Implementation Checklist](./implementation-checklist.md)
- [AEGIS-DEVELOPER-STUDIO.md](./AEGIS-DEVELOPER-STUDIO.md)
- [CROSS-PROJECT-DEVELOPMENT-STATUS-2026-09-02.md](./CROSS-PROJECT-DEVELOPMENT-STATUS-2026-09-02.md)

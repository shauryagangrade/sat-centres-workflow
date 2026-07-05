# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| `1.x`   | ✅ Active  |
| `< 1.0` | ❌ No longer supported |

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Email: **shauryagangrade11@gmail.com**

Include in your report:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested fix (optional)

### Response Timeline

| Stage | Target |
|-------|--------|
| Acknowledgement | Within 48 hours |
| Status update | Within 7 days |
| Patch or mitigation | Within 30 days for critical; 90 days for moderate |

## Scope

**In scope:**
- Command injection via user-supplied cURL input
- Arbitrary file write / path traversal in dataset outputs
- Sensitive data exposure (API keys, cached tokens)
- Dependency with a known CVE affecting this project

**Out of scope:**
- Vulnerabilities in third-party geocoding services (report to them directly)
- Social engineering
- Theoretical vulnerabilities without a proof of concept

## Security Hall of Fame

| Researcher | Issue | Date |
|------------|-------|------|
| — | — | — |

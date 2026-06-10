# Security Policy

## Supported Versions

We provide security updates for the following versions:

| Version | Supported Until |
|---------|-----------------|
| 0.1.x   | 2027-05-23      |
| < 0.1.0 | ❌ Unsupported  |

## Reporting a Vulnerability

To report a security vulnerability, please use the [GitHub Security Advisory](https://github.com/syncdoc-dev/syncdoc-free/security/advisories/new) or email security@syncdoc.dev.

You should receive a response within 48 hours. If the issue is confirmed, we will:
1. Acknowledge receipt of your report
2. Investigate the issue
3. Provide regular updates on our progress
4. Coordinate the release of any necessary fixes or mitigations

Please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Any proof-of-concept code or screenshots

## Security Best Practices for Self-Hosted Deployments

### Environment Configuration

1. **Change Default Secrets**
   - Always change `JWT_SECRET_KEY` from the default value
   - Use strong, randomly generated secrets (minimum 32 characters)
   - Example: `openssl rand -hex 32`

2. **Database Security**
   - Use strong passwords for PostgreSQL
   - Consider enabling SSL/TLS for database connections
   - Restrict database network access to application servers only
   - Regularly backup your database

3. **Redis Security**
   - Require authentication for Redis connections
   - Bind Redis to localhost or private network interfaces only
   - Consider enabling Redis TLS support

4. **File System Permissions**
   - Ensure the application runs as a non-root user
   - Set appropriate file permissions on mounted volumes
   - Regularly audit file system access

### Network Security

1. **Network Segmentation**
   - Place database and Redis on private networks
   - Use firewalls to restrict access to essential ports only
   - Consider using a service mesh for inter-service communication

2. **Transport Encryption**
   - Terminate TLS at a reverse proxy (NGINX, Traefik, etc.)
   - Use strong cipher suites and protocols (TLS 1.2+)
   - Regularly update SSL certificates

3. **API Security**
   - Implement rate limiting to prevent abuse
   - Use CORS policies to restrict allowed origins
   - Validate and sanitize all inputs
   - Implement proper authentication and authorization

### Application Security

1. **Dependency Management**
   - Regularly update dependencies
   - Monitor for known vulnerabilities in dependencies
   - Use tools like `safety` or `dependabot` for vulnerability scanning

2. **Container Security**
   - Run containers as non-root users
   - Scan container images for vulnerabilities
   - Use minimal base images (distroless when possible)
   - Implement read-only root filesystems where possible

3. **Logging and Monitoring**
   - Enable comprehensive logging
   - Monitor logs for suspicious activity
   - Set up alerts for failed login attempts, unusual access patterns
   - Consider integrating with SIEM solutions

### Data Protection

1. **Data Encryption**
   - Encrypt sensitive data at rest (database fields, file storage)
   - Use encryption keys managed by a KMS or secrets manager
   - Regularly rotate encryption keys

2. **Privacy Considerations**
   - Minimize collection of personally identifiable information (PII)
   - Implement data retention policies
   - Provide mechanisms for data export and deletion (GDPR/CCPA compliance)
   - Anonymize or pseudonymize data where possible

### Incident Response

1. **Preparation**
   - Maintain up-to-date incident response playbooks
   - Regularly test backup and restore procedures
   - Keep emergency contact information current

2. **Detection**
   - Implement intrusion detection systems
   - Monitor for unusual system behavior
   - Set up file integrity monitoring

3. **Containment**
   - Isolate affected systems
   - Preserve evidence for investigation
   - Notify relevant stakeholders

4. **Eradication and Recovery**
   - Remove malicious elements
   - Restore systems from clean backups
   - Verify system integrity before returning to service

5. **Post-Incident Activity**
   - Conduct thorough post-mortem analysis
   - Update security measures based on lessons learned
   - Improve detection and response capabilities

## Security Features in SyncDoc

### Authentication & Authorization
- JWT-based authentication
- bcrypt password hashing
- Role-based access control (RBAC)
- GitHub OAuth integration with callback state validation
- Baseline in-process rate limits for authentication endpoints
- Secure password reset functionality

### Input Validation
- Pydantic models for request/response validation
- SQLAlchemy ORM to prevent SQL injection
- Allowlisted remote source hosts with private-network blocking by default
- Explicit root confinement for newly added local filesystem sources

### Secure Communications
- HTTPS enforcement (via reverse proxy)
- Secure WebSocket connections (WSS)
- JWT tokens transmitted via Authorization header
- Same-site, HTTP-only cookies for OAuth state

### Auditing & Logging
- Application and worker logging

### Dependency Security
- Locked dependencies for reproducible builds

## Compliance

SyncDoc does not claim certification or compliance with a particular framework. Operators
are responsible for deployment controls, retention, monitoring, backups, and regulatory
requirements.

## Security Updates

Security patches are released as needed and documented in:
- GitHub Releases
- Security Advisories
- Changelog entries

We recommend enabling automated security updates for dependencies and regularly checking for new releases of SyncDoc itself.

## Contact

For security-related questions or concerns:
- Email: security@syncdoc.dev
- GitHub: https://github.com/syncdoc-dev/syncdoc-free/security/advisories

We appreciate your help in keeping SyncDoc secure for everyone!

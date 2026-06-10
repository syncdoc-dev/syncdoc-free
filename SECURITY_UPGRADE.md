# Security Hardening Upgrade Notes

This change is designed to preserve existing deployed data and credentials, but it includes
intentional behavior changes.

## Breaking or Behavior-Changing Items

1. The unauthenticated `/api/admin/db/tables` database browser endpoints are removed.
2. Newly registered users receive a new isolated organization with the `owner` role. They no
   longer join the first/default organization.
3. Newly added remote sources must use HTTPS or SSH and match `ALLOWED_SOURCE_HOSTS`.
   Hosts resolving to private or non-public addresses also require
   `ALLOW_PRIVATE_SOURCE_HOSTS=true`.
4. Newly added local sources require `ALLOW_LOCAL_SOURCES=true` and must resolve beneath
   `SOURCE_IMPORT_ROOT`.
5. Runtime settings saved after the migration are organization-scoped. Existing global
   settings remain available as fallback values until an organization saves an override.
6. GitHub OAuth returns the JWT in the URL fragment instead of the query string. The bundled
   frontend supports this behavior; custom clients must read `#token=...`.
7. Updating runtime settings now requires the `owner` role instead of `admin`.
8. API CORS access is restricted to the configured `FRONTEND_URL`; additional custom
   frontend origins require deployment-specific proxy or CORS configuration.

## Preserved Compatibility

- Existing source records are not rewritten or disabled. The new source checks apply when a
  source is created or inspected.
- Existing credentials encrypted with `JWT_SECRET_KEY` remain decryptable after a separate
  `CREDENTIAL_ENCRYPTION_KEY` is configured.
- The settings migration preserves existing rows as global fallback values.
- Docker Compose keeps self-registration enabled by default to preserve current deployment
  behavior. New non-Compose installations use the safer application default of disabled.
- Weak production JWT secrets warn by default. Set `STRICT_SECURITY_CONFIG=true` to convert
  the warning into a startup failure after secrets have been rotated.

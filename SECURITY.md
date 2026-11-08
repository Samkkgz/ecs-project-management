# Security Policy

## Supported Versions

| Version | Supported |
|---|---|
| 2.0.x | ✅ |
| < 2.0.5 | ❌ |

## Reporting a Vulnerability

Please **do not** open a public issue for security problems.

- Preferred: GitHub Security Advisories → "Report a vulnerability"
- Alternative: email `sam.lu@ecsomni.com` with steps to reproduce and impact

We aim to acknowledge reports within 3 business days.

## Deployment Checklist

- [ ] `POSTGRES_PASSWORD`, `SECRET_KEY`, `JWT_SECRET` are unique random values (≥ 32 chars)
- [ ] `.env` is excluded from version control and readable only by the service account
- [ ] The app is served over HTTPS and `COOKIE_SECURE=true`
- [ ] Database port is not published to the public network
- [ ] Bootstrap admin password from `initial_admin_password.txt` is changed/removed after first login
- [ ] Backups contain code, database dump and uploaded files

## Rotation Notes

- Rotating `JWT_SECRET` invalidates all existing sessions (expected).
- Rotating `POSTGRES_PASSWORD` requires `ALTER USER ecs WITH PASSWORD '...'` in PostgreSQL before restarting the app.

# Safe HTTP Defaults Design

## Goal

Add conservative, role-wide HTTP defaults that reduce static-asset transfer
size, correct the Web App Manifest media type, and avoid Nginx version
disclosure without changing application routing or browser-enforced policy.

## Included defaults

- Map `.webmanifest` to `application/manifest+json` in the role's top-level
  `http` block.
- Enable gzip for text-based static response types, emit `Vary:
  Accept-Encoding`, and retain Nginx's default exclusion of proxied responses.
- Disable Nginx version tokens.

## Explicitly excluded

- HSTS, CSP, Permissions-Policy, and response `add_header` defaults. These
  require vhost/application-specific review; legacy Nginx header inheritance
  also makes a global `add_header` insufficient when locations add cache
  headers.
- Brotli and an Nginx package upgrade. They require separate package/module or
  platform work.

## Availability safeguards

The role's rendered configuration must pass `nginx -t` before Nginx reloads.
The test suite asserts the generated global directives. Deployment uses the
existing role handler, so an invalid configuration is not reloaded. After
deployment, probe every managed HTTPS host for a successful response; check
one JavaScript asset with `Accept-Encoding: gzip` and check a manifest response
for `application/manifest+json`. Roll back by restoring the prior role commit
and rerunning the playbook if a probe fails.

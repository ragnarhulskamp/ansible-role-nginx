# Safe HTTP Defaults Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provide low-risk Nginx defaults for Web App Manifest MIME type, text-asset gzip compression, and suppressed version tokens.

**Architecture:** Keep the behavior in the role's top-level `http` template so it applies uniformly to every managed vhost. Expose gzip settings as conservative role defaults. Do not add browser policy headers or change vhost routing.

**Tech Stack:** Ansible/Jinja2, Python unittest with PyYAML, Nginx configuration validation.

---

### Task 1: Add conservative global HTTP defaults

**Files:**
- Modify: `tests/test_nginx_role_structure.py`
- Modify: `defaults/main.yml`
- Modify: `templates/nginx.conf.j2`

- [ ] **Step 1: Write the failing structural test**

Add this test method to `NginxRoleStructureTests`:

```python
    def test_http_defaults_enable_safe_static_delivery(self):
        defaults = load_yaml("defaults/main.yml")
        template = (REPO / "templates/nginx.conf.j2").read_text(encoding="utf-8")

        self.assertEqual(defaults["nginx_server_tokens"], "off")
        self.assertEqual(defaults["nginx_gzip"], "on")
        self.assertEqual(defaults["nginx_gzip_vary"], "on")
        self.assertEqual(defaults["nginx_gzip_min_length"], 1024)
        self.assertIn("application/manifest+json webmanifest;", template)
        self.assertIn("gzip {{ nginx_gzip }};", template)
        self.assertIn("gzip_vary {{ nginx_gzip_vary }};", template)
        self.assertIn("gzip_min_length {{ nginx_gzip_min_length }};", template)
        self.assertIn("application/javascript", template)
        self.assertIn("application/manifest+json", template)
```

- [ ] **Step 2: Verify the test fails for missing defaults**

Run: `PYENV_VERSION=3.12.2 python -m unittest tests/test_nginx_role_structure.py`

Expected: failure because the gzip defaults and MIME mapping do not yet exist, and `nginx_server_tokens` is still `on`.

- [ ] **Step 3: Add the minimum role configuration**

Set these defaults in `defaults/main.yml`:

```yaml
nginx_server_tokens: "off"
nginx_gzip: "on"
nginx_gzip_vary: "on"
nginx_gzip_min_length: 1024
nginx_gzip_types:
  - text/plain
  - text/css
  - application/javascript
  - application/json
  - application/manifest+json
  - image/svg+xml
```

In the `http` block of `templates/nginx.conf.j2`, add the Web App Manifest
mapping beside `default_type`, and replace the commented gzip block with:

```jinja2
{% block http_gzip %}
    gzip {{ nginx_gzip }};
    gzip_vary {{ nginx_gzip_vary }};
    gzip_min_length {{ nginx_gzip_min_length }};
    gzip_types {{ nginx_gzip_types | join(' ') }};
{% endblock %}
```

Do not set `gzip_proxied`; leaving it at Nginx's default avoids enabling
compression for proxied responses. Do not add HSTS, CSP, Permissions-Policy,
or any `add_header` directives.

- [ ] **Step 4: Verify the role tests pass**

Run: `PYENV_VERSION=3.12.2 python -m unittest tests/test_nginx_role_structure.py`

Expected: all 14 tests pass.

- [ ] **Step 5: Verify generated Nginx syntax in Molecule**

Run: `PYENV_VERSION=3.12.2 molecule test`

Expected: scenario completes and its `nginx -t` verification succeeds.

- [ ] **Step 6: Commit the implementation**

```bash
git add defaults/main.yml templates/nginx.conf.j2 tests/test_nginx_role_structure.py docs/superpowers/plans/2026-10-03-safe-http-defaults.md
git commit -m "feat: add safe HTTP defaults"
```

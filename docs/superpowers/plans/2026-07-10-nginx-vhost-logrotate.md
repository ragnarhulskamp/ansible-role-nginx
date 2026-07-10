# Nginx Vhost Logrotate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a role-managed wildcard logrotate rule for `/srv/www/<vhost>/logs/*.log`.

**Architecture:** The nginx role will render one logrotate config file at `/etc/logrotate.d/nginx-vhost-logs`. Defaults expose the size threshold and retention count; the template owns the wildcard rule and nginx log-reopen postrotate command.

**Tech Stack:** Ansible role tasks/templates/defaults, Python `unittest` structure tests, Molecule Ansible verification.

---

### Task 1: Structure Tests

**Files:**
- Modify: `tests/test_nginx_role_structure.py`
- Test: `tests/test_nginx_role_structure.py`

- [ ] **Step 1: Write the failing tests**

Add these tests to `tests/test_nginx_role_structure.py`:

```python
    def test_vhost_logrotate_defaults_are_configurable(self):
        defaults = load_yaml("defaults/main.yml")
        self.assertEqual(defaults["nginx_vhost_logrotate_min_size"], "10M")
        self.assertEqual(defaults["nginx_vhost_logrotate_rotate"], 30)

    def test_main_tasks_install_and_manage_vhost_logrotate(self):
        tasks = load_yaml("tasks/main.yml")
        package_task = next(task for task in tasks if task["name"] == "Ensure logrotate is installed.")
        self.assertEqual(package_task["package"]["name"], "logrotate")
        self.assertEqual(package_task["package"]["state"], "present")
        self.assertTrue(package_task["become"])

        template_task = next(task for task in tasks if task["name"] == "Copy nginx vhost logrotate configuration in place")
        self.assertEqual(template_task["template"]["src"], "nginx-vhost-logrotate.j2")
        self.assertEqual(template_task["template"]["dest"], "/etc/logrotate.d/nginx-vhost-logs")
        self.assertEqual(template_task["template"]["owner"], "root")
        self.assertEqual(template_task["template"]["group"], "{{ root_group }}")
        self.assertEqual(template_task["template"]["mode"], 0o644)
        self.assertTrue(template_task["become"])

    def test_vhost_logrotate_template_uses_wildcard_policy_and_reopens_logs(self):
        template = (REPO / "templates/nginx-vhost-logrotate.j2").read_text(encoding="utf-8")
        self.assertIn("{{ nginx_www_root }}/*/logs/*.log {", template)
        self.assertIn("daily", template)
        self.assertIn("minsize {{ nginx_vhost_logrotate_min_size }}", template)
        self.assertIn("rotate {{ nginx_vhost_logrotate_rotate }}", template)
        self.assertIn("compress", template)
        self.assertIn("delaycompress", template)
        self.assertIn("missingok", template)
        self.assertIn("notifempty", template)
        self.assertIn("create 0644 {{ nginx_user }} {{ nginx_user }}", template)
        self.assertIn("sharedscripts", template)
        self.assertIn("postrotate", template)
        self.assertIn("nginx -s reopen", template)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
python -m unittest tests.test_nginx_role_structure
```

Expected: FAIL because `nginx_vhost_logrotate_min_size` and the logrotate template/task do not exist yet.

### Task 2: Role Implementation

**Files:**
- Modify: `defaults/main.yml`
- Modify: `tasks/main.yml`
- Create: `templates/nginx-vhost-logrotate.j2`
- Test: `tests/test_nginx_role_structure.py`

- [ ] **Step 1: Add defaults**

Add below `nginx_www_root` in `defaults/main.yml`:

```yaml
nginx_vhost_logrotate_min_size: "10M"
nginx_vhost_logrotate_rotate: 30
```

- [ ] **Step 2: Add logrotate tasks**

Add these tasks in `tasks/main.yml` after nginx installation setup includes and before vhost configuration:

```yaml
- name: Ensure logrotate is installed.
  package:
    name: logrotate
    state: present
  become: yes

- name: Copy nginx vhost logrotate configuration in place
  template:
    src: nginx-vhost-logrotate.j2
    dest: /etc/logrotate.d/nginx-vhost-logs
    owner: root
    group: "{{ root_group }}"
    mode: 0644
  become: yes
```

- [ ] **Step 3: Add the logrotate template**

Create `templates/nginx-vhost-logrotate.j2`:

```jinja
{{ nginx_www_root }}/*/logs/*.log {
    daily
    minsize {{ nginx_vhost_logrotate_min_size }}
    rotate {{ nginx_vhost_logrotate_rotate }}
    compress
    delaycompress
    missingok
    notifempty
    create 0644 {{ nginx_user }} {{ nginx_user }}
    sharedscripts
    postrotate
        nginx -s reopen >/dev/null 2>&1 || true
    endscript
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```bash
python -m unittest tests.test_nginx_role_structure
```

Expected: PASS.

### Task 3: Molecule Verification

**Files:**
- Modify: `molecule/default/verify.yml`
- Test: `molecule/default/verify.yml`

- [ ] **Step 1: Extend Molecule file assertions**

Add `/etc/logrotate.d/nginx-vhost-logs` to the `Inspect generated nginx files` loop in `molecule/default/verify.yml`:

```yaml
        - /etc/logrotate.d/nginx-vhost-logs
```

- [ ] **Step 2: Run role tests**

Run:

```bash
python -m unittest tests.test_nginx_role_structure
```

Expected: PASS.

- [ ] **Step 3: Run Molecule when available**

Run:

```bash
molecule test
```

Expected: PASS with nginx syntax valid and `/etc/logrotate.d/nginx-vhost-logs` present.

### Task 4: Commit

**Files:**
- Modify: `defaults/main.yml`
- Modify: `tasks/main.yml`
- Create: `templates/nginx-vhost-logrotate.j2`
- Modify: `tests/test_nginx_role_structure.py`
- Modify: `molecule/default/verify.yml`
- Create: `docs/superpowers/plans/2026-07-10-nginx-vhost-logrotate.md`

- [ ] **Step 1: Review only intended changes**

Run:

```bash
git diff -- defaults/main.yml tasks/main.yml templates/nginx-vhost-logrotate.j2 tests/test_nginx_role_structure.py molecule/default/verify.yml docs/superpowers/plans/2026-07-10-nginx-vhost-logrotate.md
```

Expected: diff contains only logrotate defaults, tasks, template, tests, Molecule assertion, and this plan.

- [ ] **Step 2: Commit scoped files**

Run:

```bash
git add defaults/main.yml tasks/main.yml templates/nginx-vhost-logrotate.j2 tests/test_nginx_role_structure.py molecule/default/verify.yml docs/superpowers/plans/2026-07-10-nginx-vhost-logrotate.md
git commit -m "feat: rotate nginx vhost logs"
```

Expected: commit succeeds without staging unrelated local edits.

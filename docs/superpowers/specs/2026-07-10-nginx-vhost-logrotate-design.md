# Nginx Vhost Logrotate Design

## Purpose

The nginx role creates per-vhost log directories under `{{ nginx_www_root }}/<vhost>/logs` and the Magtar vhost template writes `access.log` and `error.log` there. The distro nginx logrotate configuration only covers standard nginx log paths such as `/var/log/nginx/*.log`, so role-managed vhost logs need their own rotation policy.

## Design

The role will manage a single logrotate file at `/etc/logrotate.d/nginx-vhost-logs`. The rule will match `{{ nginx_www_root }}/*/logs/*.log`, which covers all current and future role-managed vhost log directories without generating one file per vhost.

The default policy will be:

- check daily through the host's normal logrotate schedule
- rotate only when a log reaches `10M`
- keep `30` rotations
- compress old rotations with `compress` and `delaycompress`
- tolerate missing and empty logs with `missingok` and `notifempty`
- create replacement logs owned by `{{ nginx_user }}:{{ nginx_user }}`
- use `sharedscripts` and signal nginx in `postrotate` so nginx reopens rotated logs

The size threshold and rotation count will be configurable with defaults:

```yaml
nginx_vhost_logrotate_min_size: "10M"
nginx_vhost_logrotate_rotate: 30
```

## Components

- `defaults/main.yml`: expose logrotate defaults.
- `templates/nginx-vhost-logrotate.j2`: render the wildcard logrotate rule.
- `tasks/main.yml`: install `logrotate` and deploy `/etc/logrotate.d/nginx-vhost-logs`.
- `tests/test_nginx_role_structure.py`: assert the task, template path, wildcard, defaults, and postrotate signal.
- `molecule/default/verify.yml`: assert the rendered logrotate file exists in the default scenario.

## Error Handling

The logrotate rule will use `missingok` so absent vhost logs do not fail rotation. It will use `notifempty` to skip empty log files. The postrotate command will tolerate nginx not being active during provisioning or test runs.

## Testing

Add structure tests before implementation to prove the feature is missing, then implement the minimal role changes to pass. Run the nginx role structure tests and, if available in the environment, the nginx Molecule scenario.

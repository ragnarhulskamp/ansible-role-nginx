from pathlib import Path
import unittest

import yaml


REPO = Path(__file__).resolve().parents[1]


def load_yaml(relative_path):
    with (REPO / relative_path).open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


class NginxRoleStructureTests(unittest.TestCase):
    def test_main_tasks_configure_nginx_conf_once(self):
        tasks = load_yaml("tasks/main.yml")
        nginx_conf_tasks = [
            task
            for task in tasks
            if task.get("template", {}).get("dest") == "{{ nginx_conf_file_path }}"
        ]
        self.assertEqual(len(nginx_conf_tasks), 1)
        self.assertEqual(nginx_conf_tasks[0]["name"], "Copy nginx configuration in place")

    def test_variable_setup_runs_for_tagged_operations(self):
        tasks = load_yaml("tasks/main.yml")
        include_vars = next(task for task in tasks if task["name"] == "Include OS-specific variables.")
        define_user = next(task for task in tasks if task["name"] == "Define nginx_user.")
        self.assertEqual(include_vars["tags"], ["always"])
        self.assertEqual(define_user["tags"], ["always"])

    def test_redhat_setup_include_runs_for_tagged_logrotate(self):
        tasks = load_yaml("tasks/main.yml")
        redhat_include = next(task for task in tasks if task.get("include_tasks") == "setup-RedHat.yml")
        self.assertEqual(redhat_include["tags"], ["always"])

    def test_absent_vhosts_remove_managed_directory(self):
        tasks = load_yaml("tasks/vhosts.yml")
        remove_dir = next(task for task in tasks if task["name"] == "Remove managed vhost directory")
        self.assertEqual(remove_dir["file"]["state"], "absent")
        self.assertEqual(
            remove_dir["when"],
            "item.state | default('present') == 'absent'",
        )

    def test_magtar_template_uses_boolean_ssl_and_php_switches(self):
        template = (REPO / "templates/vhost-magtar-default.j2").read_text(encoding="utf-8")
        self.assertIn("item.redirect_http_to_https | default('443' in listen_value) | bool", template)
        self.assertIn("item.php | default(false) | bool", template)
        self.assertIn("item.standard_ssl | default(false) | bool", template)
        self.assertIn("php_fpm_listen | default('/run/php-fpm/www.sock')", template)
        self.assertIn("/etc/pki/tls/lego/certificates/{{ item.cert_name }}.pem", template)

    def test_default_vhost_template_renders_optional_ipv6_listener(self):
        template = (REPO / "templates/vhost.j2").read_text(encoding="utf-8")
        self.assertIn("{% if item.listen6 is defined %}", template)
        self.assertIn("listen {{ item.listen6 }};", template)

    def test_vhost_logrotate_defaults_are_configurable(self):
        defaults = load_yaml("defaults/main.yml")
        self.assertIn("nginx_vhost_logrotate_min_size", defaults)
        self.assertIn("nginx_vhost_logrotate_rotate", defaults)
        self.assertEqual(defaults["nginx_vhost_logrotate_min_size"], "10M")
        self.assertEqual(defaults["nginx_vhost_logrotate_rotate"], 30)

    def test_main_tasks_install_and_manage_vhost_logrotate(self):
        tasks = load_yaml("tasks/main.yml")
        package_tasks = [task for task in tasks if task.get("name") == "Ensure logrotate is installed."]
        self.assertEqual(len(package_tasks), 1)
        package_task = package_tasks[0]
        self.assertEqual(package_task["package"]["name"], "logrotate")
        self.assertEqual(package_task["package"]["state"], "present")
        self.assertEqual(package_task["when"], "ansible_os_family != 'RedHat'")
        self.assertEqual(package_task["tags"], ["nginx_logrotate"])
        self.assertTrue(package_task["become"])

        template_tasks = [
            task for task in tasks if task.get("name") == "Copy nginx vhost logrotate configuration in place"
        ]
        self.assertEqual(len(template_tasks), 1)
        template_task = template_tasks[0]
        self.assertEqual(template_task["template"]["src"], "nginx-vhost-logrotate.j2")
        self.assertEqual(template_task["template"]["dest"], "/etc/logrotate.d/nginx-vhost-logs")
        self.assertEqual(template_task["template"]["owner"], "root")
        self.assertEqual(template_task["template"]["group"], "{{ root_group }}")
        self.assertEqual(template_task["template"]["mode"], 0o644)
        self.assertEqual(template_task["tags"], ["nginx_logrotate"])
        self.assertTrue(template_task["become"])

    def test_vhost_logrotate_template_uses_wildcard_policy_and_reopens_logs(self):
        template_path = REPO / "templates/nginx-vhost-logrotate.j2"
        self.assertTrue(template_path.exists())
        template = template_path.read_text(encoding="utf-8")
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

    def test_redhat_setup_manages_selinux_backend_ports(self):
        tasks = load_yaml("tasks/setup-RedHat.yml")
        self.assertIn("nginx_backend_http_ports", load_yaml("defaults/main.yml"))
        setup_text = (REPO / "tasks/setup-RedHat.yml").read_text(encoding="utf-8")
        self.assertIn("semanage port -l", setup_text)
        self.assertIn("http_port_t", setup_text)
        self.assertIn("nginx_backend_http_ports", setup_text)

        nginx_install = next(task for task in tasks if task["name"] == "Ensure nginx is installed.")
        self.assertIn("ansible.builtin.raw", nginx_install)
        self.assertIn("__nginx_install_changed__", nginx_install["ansible.builtin.raw"])
        self.assertEqual(nginx_install["args"]["executable"], "/bin/bash")
        self.assertEqual(
            nginx_install["changed_when"],
            "'__nginx_install_changed__' in (nginx_install.stdout | default(''))",
        )

        selinux_tools = next(task for task in tasks if task["name"] == "Ensure SELinux port management tools are installed.")
        self.assertEqual(selinux_tools["args"]["executable"], "/bin/bash")

        selinux_ports = next(task for task in tasks if task["name"] == "Allow nginx backend ports in SELinux")
        self.assertEqual(selinux_ports["args"]["executable"], "/bin/bash")

    def test_redhat_setup_installs_logrotate_without_dnf_module(self):
        tasks = load_yaml("tasks/setup-RedHat.yml")
        logrotate_install = next(task for task in tasks if task["name"] == "Ensure logrotate is installed.")
        self.assertIn("ansible.builtin.raw", logrotate_install)
        self.assertIn("rpm -q logrotate", logrotate_install["ansible.builtin.raw"])
        self.assertIn("dnf -y install logrotate", logrotate_install["ansible.builtin.raw"])
        self.assertIn("yum -y install logrotate", logrotate_install["ansible.builtin.raw"])
        self.assertIn("__nginx_logrotate_install_changed__", logrotate_install["ansible.builtin.raw"])
        self.assertEqual(logrotate_install["args"]["executable"], "/bin/bash")
        self.assertEqual(
            logrotate_install["changed_when"],
            "'__nginx_logrotate_install_changed__' in (nginx_logrotate_install.stdout | default(''))",
        )
        self.assertEqual(logrotate_install["tags"], ["nginx_logrotate"])
        self.assertTrue(logrotate_install["become"])

    def test_molecule_default_scenario_uses_podman_rocky8_and_ansible_verify(self):
        molecule = load_yaml("molecule/default/molecule.yml")
        self.assertEqual(molecule["driver"]["name"], "podman")
        self.assertEqual(molecule["platforms"][0]["image"], "geerlingguy/docker-rockylinux8-ansible:latest")
        self.assertEqual(
            molecule["provisioner"]["env"]["ANSIBLE_ROLES_PATH"],
            "${MOLECULE_PROJECT_DIRECTORY}/..",
        )
        self.assertEqual(molecule["verifier"]["name"], "ansible")
        self.assertIn("verify", molecule["scenario"]["test_sequence"])

        verify = load_yaml("molecule/default/verify.yml")
        commands = [task["ansible.builtin.command"] for task in verify[0]["tasks"] if "ansible.builtin.command" in task]
        self.assertIn("nginx -t", commands)

    def test_galaxy_metadata_has_valid_role_name_for_molecule(self):
        galaxy_info = load_yaml("meta/main.yml")["galaxy_info"]
        self.assertEqual(galaxy_info["namespace"], "geerlingguy")
        self.assertEqual(galaxy_info["role_name"], "nginx")

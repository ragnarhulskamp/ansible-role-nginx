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

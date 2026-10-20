from pathlib import Path
import subprocess,unittest,yaml
from jinja2 import Template
ROOT=Path(__file__).resolve().parents[1]
class BackendPortMapping(unittest.TestCase):
 def test_existing_port_after_first_column_does_not_mutate_selinux(self):
  tasks=yaml.safe_load((ROOT/'tasks/setup-RedHat.yml').read_text())
  task=next(t for t in tasks if t.get('name')=='Allow nginx backend ports in SELinux')
  command=Template(task['ansible.builtin.raw']).render(item=8080)
  stub='''semanage() {
if [ "$1 $2" = "port -l" ]; then
printf 'http_port_t tcp 80, 443, 8080, 8443\n'
else
printf 'Unexpected SELinux mutation\n' >&2
return 77
fi
}
'''
  result=subprocess.run(['bash','-c',stub+command],text=True,capture_output=True)
  self.assertEqual(result.returncode,0,result.stderr)
  self.assertNotIn('changed',result.stdout)

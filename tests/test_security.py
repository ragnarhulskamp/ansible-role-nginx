from pathlib import Path
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]


class WebSecurityTests(unittest.TestCase):
    def test_shared_tls_defaults_use_current_protocols_and_aead(self):
        defaults = yaml.safe_load((ROOT / 'defaults/main.yml').read_text())
        self.assertEqual(defaults.get('nginx_ssl_protocols'), 'TLSv1.2 TLSv1.3')
        ciphers = defaults.get('nginx_ssl_ciphers', '')
        self.assertIn('GCM', ciphers)
        self.assertNotIn('CBC', ciphers)
        self.assertNotIn('HIGH', ciphers)

    def test_shared_security_headers_are_available_to_cache_locations(self):
        path = ROOT / 'templates/security-headers.j2'
        self.assertTrue(path.exists())
        text = path.read_text()
        for header in ['Strict-Transport-Security', 'X-Content-Type-Options',
                       'X-Frame-Options', 'Referrer-Policy']:
            self.assertIn(header, text)
        self.assertNotIn('includeSubDomains', text)
        self.assertNotIn('preload', text)
        tasks = (ROOT / 'tasks/main.yml').read_text()
        self.assertIn('security-headers.j2', tasks)

    def test_official_package_repository_requires_https_and_signature_verification(self):
        text = (ROOT / 'templates/nginx.repo.j2').read_text()
        self.assertIn('baseurl=https://', text)
        self.assertIn('gpgcheck=1', text)
        self.assertIn('gpgkey=https://nginx.org/keys/nginx_signing.key', text)


if __name__ == '__main__':
    unittest.main()

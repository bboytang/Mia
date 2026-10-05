import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class AccountDeploymentTests(unittest.TestCase):
    def test_install_preserves_configuration_and_account_database(self):
        source = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            server = root / "repo/server"
            (server / "deploy").mkdir(parents=True)
            (server / "requirements.txt").write_text("")
            (server / "deploy/mia-gateway.service.example").write_text(
                (source / "deploy/mia-gateway.service.example").read_text())
            script = (source / "deploy/install-ubuntu.sh").read_text()
            for target in ("/opt/mia", "/etc/mia", "/etc/systemd/system", "/var/lib/mia"):
                script = script.replace(target, str(root) + target)
            installer = server / "deploy/install-ubuntu.sh"
            installer.write_text(script)
            (root / "etc/systemd/system").mkdir(parents=True)
            venv = root / "opt/mia/.venv/bin"
            venv.mkdir(parents=True)
            venv.joinpath("python").symlink_to(Path(os.sys.executable))
            commands = root / "commands"
            commands.mkdir()
            for command in ("apt-get", "getent", "groupadd", "useradd", "chown", "runuser", "systemctl"):
                wrapper = commands / command
                wrapper.write_text("#!/bin/bash\nexit 0\n")
                wrapper.chmod(0o700)
            identity = commands / "id"
            identity.write_text("#!/bin/bash\necho 0\n")
            identity.chmod(0o700)
            install = commands / "install"
            install.write_text('''#!/bin/bash
args=()
while (( $# )); do
  case "$1" in -o|-g) shift 2;; *) args+=("$1"); shift;; esac
done
exec /usr/bin/install "${args[@]}"
''')
            install.chmod(0o700)
            env = dict(os.environ, PATH=str(commands) + ":" + os.environ["PATH"])
            config = root / "etc/mia/gateway.env"
            config.parent.mkdir(parents=True)
            original = "MIA_GATEWAY_TOKEN=maintenance-test\nLOCAL_SETTING=keep\nMIA_DAILY_ROUNDS=7\n"
            config.write_text(original)
            database = root / "var/lib/mia/accounts.sqlite3"
            database.parent.mkdir(parents=True)
            database.write_bytes(b"existing-account-data")
            for _ in range(2):
                result = subprocess.run(["bash", str(installer)], env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotIn("maintenance-test", result.stdout + result.stderr)
            contents = config.read_text()
            self.assertTrue(contents.startswith(original))
            self.assertEqual(contents.count("MIA_ACCOUNTS_ENABLED=1\n"), 1)
            self.assertIn("MIA_ACCOUNT_DB=", contents)
            self.assertIn("MIA_MAX_ACCOUNTS=100\n", contents)
            self.assertIn("MIA_MAX_CONCURRENT_ROUNDS=2\n", contents)
            self.assertNotIn("MIA_DAILY_ROUNDS=30", contents)
            self.assertEqual(config.stat().st_mode & 0o777, 0o600)
            self.assertEqual(database.read_bytes(), b"existing-account-data")
            unit = (root / "etc/systemd/system/mia-gateway.service").read_text()
            for setting in ("StateDirectory=mia", "StateDirectoryMode=0700", "UMask=0077"):
                self.assertIn(setting, unit)
            config.unlink()
            result = subprocess.run(["bash", str(installer)], env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            generated = config.read_text().splitlines()[0].split("=", 1)[1]
            self.assertEqual(len(generated), 64)
            self.assertNotIn(generated, result.stdout + result.stderr)
            self.assertIn("MIA_DAILY_ROUNDS=30\n", config.read_text())

    def test_caddy_forwards_auth_and_overwrites_untrusted_client_ip(self):
        config = (Path(__file__).resolve().parents[1] / "deploy/Caddyfile.example").read_text()
        self.assertIn("handle /api/auth/*", config)
        self.assertIn("reverse_proxy 127.0.0.1:8766", config)
        self.assertIn("header_up X-Mia-Client-IP {remote_host}", config)
        self.assertIn("handle /xiaozhi/v1/*", config)
        self.assertIn("reverse_proxy 127.0.0.1:8765", config)

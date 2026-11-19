"""Installer command construction without modifying the host or downloading packages."""
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

script = Path(__file__).resolve().parents[1] / 'scripts/install_infinisplat_runtime.py'
spec = importlib.util.spec_from_file_location('infinisplat_installer', script)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)

class InstallerTest(unittest.TestCase):
    def test_bootstraps_private_uv_and_calls_upstream_installer(self):
        with TemporaryDirectory() as directory, patch.object(installer.sys, 'argv', ['install', directory]), patch.object(installer.subprocess, 'run') as run:
            installer.main()
            self.assertEqual(run.call_count, 2)
            first = run.call_args_list[0].args[0]
            self.assertIn('uv==0.13.9', first)
            self.assertIn(str(Path(directory) / '.provision-uv'), first)
            second = run.call_args_list[1]
            self.assertEqual(second.args[0][0], str(Path(directory) / '.provision-uv/bin/uv'))
            self.assertEqual(second.kwargs['cwd'], Path(directory))

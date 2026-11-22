"""Exercise the private worker protocol without loading a GPU model."""
import base64
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

class ServerProtocolTests(unittest.TestCase):
    def test_load_generate_unload_and_eof(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            shutil.copy(Path(__file__).with_name('server.py'),root/'server.py')
            (root/'worker.py').write_text("def load_model(): return object()\ndef generate(model, body): return body['text'].encode()\n")
            program=subprocess.Popen([sys.executable,'-u',str(root/'server.py')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            self.assertEqual(json.loads(program.stdout.readline()),{'status':'loaded'})
            program.stdin.write(json.dumps({'text':'hello','voice':'soft'})+'\n');program.stdin.flush()
            self.assertEqual(base64.b64decode(json.loads(program.stdout.readline())['audio']),b'hello')
            program.stdin.write('{"action":"unload"}\n');program.stdin.flush()
            self.assertEqual(json.loads(program.stdout.readline()),{'status':'unloaded'})
            self.assertEqual(program.wait(timeout=5),0)
            program.stdin.close();program.stdout.close();program.stderr.close()

#!/usr/bin/env python3
"""One private SSH session holds the model; EOF or unload releases memory."""
import base64
import contextlib
import json
import sys
from worker import generate, load_model

MAX_REQUEST = 16384
MAX_WAV = 8 * 1024 * 1024

def reply(value):
    print(json.dumps(value, separators=(',', ':')), flush=True)

def main():
    with contextlib.redirect_stdout(sys.stderr):
        model = load_model()
    reply({'status': 'loaded'})
    while True:
        raw = sys.stdin.buffer.readline(MAX_REQUEST + 1)
        if not raw:
            return
        if len(raw) > MAX_REQUEST or not raw.endswith(b'\n'):
            reply({'error': 'Invalid request size.'})
            return
        try:
            request = json.loads(raw)
            if request == {'action': 'unload'}:
                reply({'status': 'unloaded'})
                return
            with contextlib.redirect_stdout(sys.stderr):
                audio = generate(model, request)
            if len(audio) > MAX_WAV:
                raise ValueError('Audio is too large.')
            reply({'audio': base64.b64encode(audio).decode('ascii')})
        except Exception as error:
            print('VoxCPM2 request failed:', error, file=sys.stderr)
            reply({'error': 'VoxCPM2 generation failed.'})

if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('VoxCPM2 server failed:', error, file=sys.stderr)
        sys.exit(1)

#!/usr/bin/env python3
"""Chatterbox Turbo: JSON request to PCM WAV, with optional reference."""
import base64
import contextlib
import io
import json
import os
import sys
import tempfile

MODEL = '/workspace/artflow-chatterbox/model'

def load_model():
    from chatterbox.tts_turbo import ChatterboxTurboTTS
    return ChatterboxTurboTTS.from_local(MODEL, 'cuda')

def generate(model, request):
    import soundfile as sf
    import torch
    from chatterbox.tts_turbo import Conditionals
    if not isinstance(request, dict) or set(request) not in ({'text', 'voice'}, {'text', 'voice', 'reference'}) or not isinstance(request['text'], str) or not 1 <= len(request['text'].strip()) <= 500:
        raise ValueError('Invalid request')
    model.conds = Conditionals.load(MODEL + '/conds.pt', map_location='cpu').to('cuda')
    with tempfile.TemporaryDirectory(prefix='artflow-chatterbox-') as directory:
        reference = None
        if 'reference' in request:
            data = base64.b64decode(request['reference'], validate=True)
            if len(data) > 3 * 1024 * 1024:
                raise ValueError('Reference is too large')
            reference = os.path.join(directory, 'reference.wav')
            with open(reference, 'wb') as f: f.write(data)
        with torch.inference_mode():
            audio = model.generate(request['text'].strip(), audio_prompt_path=reference)
    output = io.BytesIO()
    sf.write(output, audio.squeeze().cpu().numpy(), model.sr, format='WAV', subtype='PCM_16')
    return output.getvalue()

def main():
    raw = sys.stdin.buffer.read(5 * 1024 * 1024 + 1)
    if len(raw) > 5 * 1024 * 1024: raise ValueError('Request is too large')
    request = json.loads(raw)
    with contextlib.redirect_stdout(sys.stderr):
        audio = generate(load_model(), request)
    sys.stdout.buffer.write(audio)

if __name__ == '__main__':
    try: main()
    except Exception as error:
        print('Chatterbox failed:', error, file=sys.stderr)
        sys.exit(1)

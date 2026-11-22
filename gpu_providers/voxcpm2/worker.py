#!/usr/bin/env python3
"""VoxCPM2 worker: JSON on stdin and PCM WAV on stdout."""
import contextlib
import io
import json
import sys

MODEL = '/workspace/artflow-voxcpm2/model'

def validate(request):
    if not isinstance(request, dict) or set(request) != {'text', 'voice'}:
        raise ValueError('Invalid request')
    for field in ('text', 'voice'):
        value = request[field]
        if not isinstance(value, str) or not value.strip() or len(value) > 500:
            raise ValueError('Invalid text or voice instructions')
    return request

def load_model():
    from voxcpm import VoxCPM
    return VoxCPM.from_pretrained(MODEL, load_denoiser=False, optimize=False, device='cuda:0', local_files_only=True)

def generate(model, request):
    import soundfile as sf
    request = validate(request)
    text, voice = request['text'], request['voice']
    audio = model.generate(text='(' + voice.strip() + ')' + text.strip(), cfg_value=2.0, inference_timesteps=10, max_len=1024)
    result = io.BytesIO()
    sf.write(result, audio, model.tts_model.sample_rate, format='WAV', subtype='PCM_16')
    return result.getvalue()

def main():
    raw = sys.stdin.buffer.read(16385)
    if len(raw) > 16384:
        raise ValueError('Request too large')
    request = validate(json.loads(raw))
    with contextlib.redirect_stdout(sys.stderr):
        audio = generate(load_model(), request)
    sys.stdout.buffer.write(audio)

if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('VoxCPM2 failed:', error, file=sys.stderr)
        sys.exit(1)

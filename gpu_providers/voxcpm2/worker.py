#!/usr/bin/env python3
"""VoxCPM2 worker: JSON on stdin and PCM WAV on stdout."""
import contextlib
import io
import json
import sys

MODEL = '/workspace/artflow-voxcpm2/model'

def main():
    raw = sys.stdin.buffer.read(16385)
    if len(raw) > 16384:
        raise ValueError('Request too large')
    request = json.loads(raw)
    if not isinstance(request, dict) or set(request) != {'text', 'voice'}:
        raise ValueError('Invalid request')
    text, voice = request['text'], request['voice']
    if not isinstance(text, str) or not text.strip() or len(text) > 500 or not isinstance(voice, str) or not voice.strip() or len(voice) > 500:
        raise ValueError('Invalid text or voice instructions')
    with contextlib.redirect_stdout(sys.stderr):
        import soundfile as sf
        from voxcpm import VoxCPM
        model = VoxCPM.from_pretrained(MODEL, load_denoiser=False, optimize=False, device='cuda:0', local_files_only=True)
        audio = model.generate(text='(' + voice.strip() + ')' + text.strip(), cfg_value=2.0, inference_timesteps=10, max_len=1024)
        result = io.BytesIO()
        sf.write(result, audio, model.tts_model.sample_rate, format='WAV', subtype='PCM_16')
    sys.stdout.buffer.write(result.getvalue())

if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('VoxCPM2 failed:', error, file=sys.stderr)
        sys.exit(1)

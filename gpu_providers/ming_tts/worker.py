#!/usr/bin/env python3
"""Bounded Ming TTS proof-of-concept worker: JSON stdin, WAV stdout."""
import contextlib
import io
import json
import sys

SOURCE = '/workspace/artflow-ming-poc/source'
MODEL = '/workspace/artflow-ming-poc/model'

def main():
    data = sys.stdin.buffer.read(16385)
    if len(data) > 16384:
        raise ValueError('Request too large')
    request = json.loads(data)
    if not isinstance(request, dict) or set(request) != {'text', 'voice'}:
        raise ValueError('Invalid request')
    text, voice = request['text'], request['voice']
    if not isinstance(text, str) or not text.strip() or len(text) > 500 or not isinstance(voice, str) or not voice.strip() or len(voice) > 500:
        raise ValueError('Invalid text or voice instructions')
    sys.path.insert(0, SOURCE)
    with contextlib.redirect_stdout(sys.stderr):
        import soundfile as sf
        from ming_tts import MingTTS
        model = MingTTS(MODEL, device='cuda:0', text_normalization=False)
        audio = model.synthesize(task='FREEFORM', language_id='English', text=text, instruction=voice, max_decode_steps=500)
        samples = audio.detach().cpu().float().numpy().squeeze()
        result = io.BytesIO()
        sf.write(result, samples, model.sample_rate, format='WAV', subtype='PCM_16')
    sys.stdout.buffer.write(result.getvalue())

if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('Ming TTS failed:', error, file=sys.stderr)
        sys.exit(1)

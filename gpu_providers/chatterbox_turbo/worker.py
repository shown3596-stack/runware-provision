#!/usr/bin/env python3
"""Generate a WAV using Chatterbox Turbo's bundled voice."""
import contextlib
import io
import json
import sys
import traceback


def main():
    request = json.load(sys.stdin)
    if set(request) != {'text', 'voice'} or not isinstance(request['text'], str) or not 1 <= len(request['text'].strip()) <= 500:
        raise ValueError('Invalid text')
    with contextlib.redirect_stdout(sys.stderr):
        from chatterbox.tts_turbo import ChatterboxTurboTTS
        import soundfile as sf
        import torch
        model = ChatterboxTurboTTS.from_local('/workspace/artflow-chatterbox/model', 'cuda')
        with torch.inference_mode():
            audio = model.generate(request['text'].strip())
        output = io.BytesIO()
        sf.write(output, audio.squeeze().cpu().numpy(), model.sr, format='WAV', subtype='PCM_16')
    sys.stdout.buffer.write(output.getvalue())


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('Chatterbox failed:', error, file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

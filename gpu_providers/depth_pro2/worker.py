#!/usr/bin/env python3
"""One-image Depth Pro 2 worker. PNG input and grayscale PNG output on stdio."""
import io
import os
import sys
import contextlib
import numpy as np

MAX_INPUT = 32 * 1024 * 1024
MAX_PIXELS = 24_000_000
MAX_SIDE = 1024


def relative_inverse_depth(values):
    values = np.asarray(values, dtype=np.float32)
    valid = np.isfinite(values) & (values > 0)
    if not np.any(valid):
        raise ValueError('Depth model returned no usable values')
    low, high = np.quantile(values[valid], (0.02, 0.98))
    if high <= low:
        return np.full(values.shape, 128, dtype=np.uint8)
    safe = np.where(valid, values, low)
    return (np.clip((safe - low) / (high - low), 0, 1) * 255).astype(np.uint8)


def main():
    from PIL import Image, ImageOps
    import torch
    from depth_pro_2 import DepthPro2
    from depth_pro_2.model import to_normalized_tensor

    payload = sys.stdin.buffer.read(MAX_INPUT + 1)
    if not payload or len(payload) > MAX_INPUT:
        raise ValueError('Invalid source image size')
    Image.MAX_IMAGE_PIXELS = MAX_PIXELS
    with Image.open(io.BytesIO(payload)) as source:
        if source.width * source.height > MAX_PIXELS:
            raise ValueError('Source image is too large')
        image = ImageOps.exif_transpose(source).convert('RGB')
    image.thumbnail((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)
    # The checkpoint is provisioned locally; inference never downloads weights.
    model_dir = os.environ.get('ARTFLOW_DEPTH_MODEL', '/workspace/artflow-depth-poc/weights-b')
    device = torch.device('cuda')
    with contextlib.redirect_stdout(sys.stderr):
        model = DepthPro2.from_pretrained(model_dir, precision=torch.bfloat16).to(device).eval()
        tensor = to_normalized_tensor(np.asarray(image), device=device).unsqueeze(0)
        with torch.inference_mode():
            prediction = model.predict_inverse_depth(tensor)[0].float().cpu().numpy()
    result = relative_inverse_depth(prediction)
    output = io.BytesIO()
    Image.fromarray(result, mode='L').save(output, format='PNG')
    sys.stdout.buffer.write(output.getvalue())


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'Depth estimation failed: {error}', file=sys.stderr)
        sys.exit(1)

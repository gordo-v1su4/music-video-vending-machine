"""Read a safetensors header and report H3 reference members without mutation."""
import argparse
import json
import struct
from pathlib import Path


def inspect(path):
    path = Path(path)
    size = path.stat().st_size
    with path.open('rb') as stream:
        prefix = stream.read(8)
        if len(prefix) != 8:
            raise ValueError('Missing safetensors header length')
        length = struct.unpack('<Q', prefix)[0]
        if length > min(100_000_000, size - 8):
            raise ValueError('Invalid or oversized safetensors header')
        header = json.loads(stream.read(length))
    raw = header.get('__metadata__', {})
    metadata = {k: json.loads(v) for k, v in raw.items()
                if k in ('refmod_meta', 'audio_refmod_meta', 'h3_refmod_meta', 'minimax_h3_refmod_meta')}
    tensors = {k: {'dtype': v.get('dtype'), 'shape': v.get('shape')}
               for k, v in header.items() if k != '__metadata__'}
    for key, value in header.items():
        if key == '__metadata__':
            continue
        offsets = value.get('data_offsets', [])
        if len(offsets) != 2 or not 0 <= offsets[0] <= offsets[1] <= size - 8 - length:
            raise ValueError(f'Invalid tensor data offsets: {key}')
    return {'path': str(path.resolve()), 'bytes': size, 'metadata': metadata,
            'tensors': tensors, 'scope': 'header inspection only; no tensor payload loaded'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files', nargs='+')
    args = parser.parse_args()
    print(json.dumps([inspect(p) for p in args.files], indent=2))

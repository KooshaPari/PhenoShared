"""Materialize the exact reviewed native source bundle for cloud builds.

The text-only connector stages a gzip tar as four base64 transport parts.
SHA-256 is checked before parsing. This archive contains application source,
not binaries, credentials, reference photographs, or user content.
"""
import base64
import gzip
import hashlib
import io
from pathlib import Path, PurePosixPath
import tarfile

root = Path(__file__).resolve().parent
transport = root.parents[1] / 'pose-build-transport'
parts = sorted(transport.glob('part*.b64'))
if len(parts) != 4:
    raise SystemExit('Expected all four source transport parts')
encoded = ''.join(p.read_text().strip() for p in parts)
packed = base64.b64decode(encoded, validate=True)
expected = '187435caeb045552f40941f94c8e3208bd43028984df20c4cd73b9a2f2866273'
actual = hashlib.sha256(packed).hexdigest()
if actual != expected:
    raise SystemExit(f'Source integrity failure: {actual}, expected {expected}')
raw = gzip.decompress(packed)
if len(raw) > 2_000_000:
    raise SystemExit('Unexpected source bundle size')
with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
    for member in archive:
        path = PurePosixPath(member.name)
        if not member.isfile() or path.is_absolute() or '..' in path.parts:
            raise SystemExit('Unsafe source archive entry')
        if path.parts[0] not in ('android', 'ios'):
            raise SystemExit('Unexpected source root')
        target = root.joinpath(*path.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        data = archive.extractfile(member).read()
        target.write_bytes(data)
        print(f'{path}: {len(data)} bytes')
print('Native source integrity verified:', actual)

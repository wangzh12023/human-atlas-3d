"""Shared encoder: pack pieces into per-system binary chunks.

Chunk layout (little-endian, gzip'd on disk as .bin.gz, decoded in browser):
  header  : magic 'HAC1', u32 version, u32 nVerts, u32 nTris, u32 nPieces, u32 flags
  float32 qmin[3], qscale[3]               (position dequantisation, shared by M and F)
  u32     pieceIds[nPieces]                (global piece index)
  u32     vertStart[nPieces+1], triStart[nPieces+1]
  u16     posM[nVerts*3]
  u16     posF[nVerts*3]   (if flags & 1)
  i8      nrmM[nVerts*2]   (octahedral)
  i8      nrmF[nVerts*2]   (if flags & 1)
  u16     localIndex[nTris*3]  (indices relative to piece vertStart; pieces < 65536 verts)
"""
import struct
import numpy as np

MAGIC = b'HAC1'
VERSION = 1


def oct_encode(n):
    n = np.asarray(n, dtype=np.float64)
    n = n / (np.abs(n).sum(1, keepdims=True) + 1e-12)
    x, y, z = n[:, 0], n[:, 1], n[:, 2]
    ox = np.where(z >= 0, x, (1 - np.abs(y)) * np.sign(x + 1e-30))
    oy = np.where(z >= 0, y, (1 - np.abs(x)) * np.sign(y + 1e-30))
    return np.clip(np.round(np.stack([ox, oy], 1) * 127), -127, 127).astype(np.int8)


def encode_chunk(pieces, ids, qmin, qscale, has_f):
    """pieces: list of dicts with vM, nM, (vF, nF), f ; ids: global indices."""
    nP = len(pieces)
    vstart = [0]; tstart = [0]
    for p in pieces:
        vstart.append(vstart[-1] + len(p['vM']))
        tstart.append(tstart[-1] + len(p['f']))
    nV, nT = vstart[-1], tstart[-1]
    flags = 1 if has_f else 0
    parts = [MAGIC, struct.pack('<5I', VERSION, nV, nT, nP, flags),
             np.asarray(qmin, np.float32).tobytes(), np.asarray(qscale, np.float32).tobytes(),
             np.asarray(ids, np.uint32).tobytes(), np.asarray(vstart, np.uint32).tobytes(), np.asarray(tstart, np.uint32).tobytes()]

    def q(v):
        return np.clip(np.round((np.asarray(v, np.float64) - qmin) / qscale), 0, 65535).astype(np.uint16)

    parts.append(np.concatenate([q(p['vM']) for p in pieces]).tobytes())
    if has_f:
        parts.append(np.concatenate([q(p['vF']) for p in pieces]).tobytes())
    parts.append(np.concatenate([oct_encode(p['nM']) for p in pieces]).tobytes())
    if has_f:
        parts.append(np.concatenate([oct_encode(p['nF']) for p in pieces]).tobytes())
    for p in pieces:
        assert len(p['vM']) < 65536, (p.get('en'), len(p['vM']))
    parts.append(np.concatenate([np.asarray(p['f'], np.uint16) for p in pieces]).tobytes())
    buf = b''.join(parts)
    pad = (-len(buf)) % 4
    return buf + b'\0' * pad

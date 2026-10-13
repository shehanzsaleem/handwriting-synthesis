"""Export the TF1 checkpoint to a plain .npz without needing TensorFlow.

A TF checkpoint is a LevelDB-style table (``.index``) mapping variable names to
``BundleEntryProto`` records, plus a raw little-endian data file. This reader
handles the uncompressed tables TensorFlow writes for checkpoints.
"""
import argparse
import struct
import sys

import numpy as np

DTYPES = {1: np.float32, 2: np.float64, 3: np.int32, 9: np.int64, 10: np.bool_}
MAGIC = 0xdb4775248b80fb57


def varint(buf, pos):
    result = shift = 0
    while True:
        b = buf[pos]
        pos += 1
        result |= (b & 0x7F) << shift
        if not b & 0x80:
            return result, pos
        shift += 7


def block_entries(buf, offset, size):
    block = buf[offset:offset + size]
    num_restarts = struct.unpack_from('<I', block, len(block) - 4)[0]
    end = len(block) - 4 - 4 * num_restarts
    pos, key = 0, b''
    while pos < end:
        shared, pos = varint(block, pos)
        unshared, pos = varint(block, pos)
        vlen, pos = varint(block, pos)
        key = key[:shared] + block[pos:pos + unshared]
        pos += unshared
        yield key, block[pos:pos + vlen]
        pos += vlen


def parse_proto(buf):
    """Minimal protobuf wire-format parser: returns {field: [values]}."""
    fields, pos = {}, 0
    while pos < len(buf):
        tag, pos = varint(buf, pos)
        field, wire = tag >> 3, tag & 7
        if wire == 0:
            val, pos = varint(buf, pos)
        elif wire == 1:
            val = buf[pos:pos + 8]
            pos += 8
        elif wire == 2:
            n, pos = varint(buf, pos)
            val = buf[pos:pos + n]
            pos += n
        elif wire == 5:
            val = buf[pos:pos + 4]
            pos += 4
        else:
            raise ValueError('unsupported wire type %d' % wire)
        fields.setdefault(field, []).append(val)
    return fields


def read_checkpoint(prefix):
    index = open(prefix + '.index', 'rb').read()
    data = open(prefix + '.data-00000-of-00001', 'rb').read()
    footer = index[-48:]
    if struct.unpack('<Q', footer[-8:])[0] != MAGIC:
        raise ValueError('not a TF table: bad magic')
    pos = 0
    _, pos = varint(footer, pos)
    _, pos = varint(footer, pos)
    idx_off, pos = varint(footer, pos)
    idx_size, pos = varint(footer, pos)
    tensors = {}
    for _, handle in block_entries(index, idx_off, idx_size):
        off, p = varint(handle, 0)
        size, _ = varint(handle, p)
        if index[off + size] != 0:
            raise ValueError('compressed tables are not supported')
        for key, value in block_entries(index, off, size):
            if not key:
                continue  # BundleHeaderProto
            entry = parse_proto(value)
            dtype = DTYPES[entry.get(1, [1])[0]]
            shape = []
            for dim in parse_proto(entry[2][0]).get(2, []) if 2 in entry else []:
                shape.append(parse_proto(dim).get(1, [0])[0])
            offset = entry.get(4, [0])[0]
            nbytes = entry.get(5, [0])[0]
            arr = np.frombuffer(data[offset:offset + nbytes], dtype=dtype).reshape(shape)
            tensors[key.decode()] = arr.copy()
    return tensors


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--checkpoint', default='checkpoints/model-17900')
    ap.add_argument('--out', default='hwsynth/data/weights.npz')
    ap.add_argument('--list', action='store_true')
    args = ap.parse_args(argv)
    tensors = read_checkpoint(args.checkpoint)
    keep = {k: v for k, v in tensors.items()
            if not any(s in k for s in ('RMSProp', 'Adam', 'Momentum', 'global_step', 'beta1_power', 'beta2_power'))}
    for k in sorted(tensors if args.list else keep):
        print(k, tensors[k].shape, tensors[k].dtype)
    if not args.list:
        np.savez_compressed(args.out, **keep)
        print('wrote', args.out, file=sys.stderr)


if __name__ == '__main__':
    main()

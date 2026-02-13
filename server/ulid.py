import os
import time
import struct

VALID_PREFIXES = frozenset([
    "ws_", "bat_", "acc_", "ctr_", "doc_", "pat_",
    "evp_", "sig_", "tri_", "aud_", "rfi_", "ann_",
    "sel_", "usr_", "wbs_", "drv_", "drc_",
    "anc_", "cor_", "oce_",
])

CROCKFORD_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _encode_crockford(value, length):
    result = []
    for _ in range(length):
        result.append(CROCKFORD_ALPHABET[value & 0x1F])
        value >>= 5
    result.reverse()
    return "".join(result)


def generate_id(prefix):
    if prefix not in VALID_PREFIXES:
        raise ValueError("Invalid prefix: %s. Must be one of: %s" % (prefix, ", ".join(sorted(VALID_PREFIXES))))

    timestamp_ms = int(time.time() * 1000)
    timestamp_encoded = _encode_crockford(timestamp_ms, 10)

    random_bytes = os.urandom(10)
    random_int = int.from_bytes(random_bytes, "big")
    random_encoded = _encode_crockford(random_int, 16)

    return "%s%s%s" % (prefix, timestamp_encoded, random_encoded)

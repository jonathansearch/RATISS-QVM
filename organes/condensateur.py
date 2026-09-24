"""Organe CONDENSATEUR Q_info : charge d'info pure (jamais de structure cible)."""
import math
import zlib
import numpy as np


def charge(n_bits=2048, seed=101):
    rng = np.random.default_rng(seed)
    return rng.integers(0, 2, n_bits).astype(np.uint8)


def entropie(bits):
    p = float(bits.mean())
    if p in (0.0, 1.0):
        return 0.0
    return float(-(p * math.log2(p) + (1 - p) * math.log2(1 - p)))


def taille_compressee(octets: bytes) -> int:
    return len(zlib.compress(octets, 9))


def injecter(points_fond, bits, n_points=60, seed=7):
    """Projection NEUTRE bits -> points (angles uniformes, jamais la cible)."""
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(bits) - 8, n_points, replace=False)
    pts = []
    for i in idx:
        octet = bits[i:i + 8]
        a = sum(int(b) << k for k, b in enumerate(octet)) / 255.0 * 2 * np.pi
        f = sum(int(x) << k for k, x in enumerate(octet[::-1])) / 255.0
        pts.append([np.cos(a) * (1.6 + 0.2 * f),
                    np.sin(a) * (1.6 + 0.2 * f), 0.5 * (f - 0.5)])
    return np.vstack([points_fond, np.array(pts)])

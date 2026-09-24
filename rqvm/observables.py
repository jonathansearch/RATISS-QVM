"""Observables du trio (zz, MI, H) — définitions synchrotron-24. MIT."""
import numpy as np


def _bits(key, n):
    k = key.replace(' ', '')
    return [(int(k[n - 1 - i]) if i < len(k) else 0) for i in range(n)]


def zz_contact(counts, q0=2, q1=3, n=6):
    tot = sum(counts.values()) or 1
    z0 = z1 = zz = 0.0
    for k, v in counts.items():
        b = _bits(k, n)
        a = 1 if b[q0] == 0 else -1
        c = 1 if b[q1] == 0 else -1
        z0 += v / tot * a
        z1 += v / tot * c
        zz += v / tot * a * c
    return zz - z0 * z1


def mi_lr(counts, n=6):
    tot = sum(counts.values()) or 1
    from collections import Counter
    pl = Counter()
    pr = Counter()
    pj = Counter()
    for k, v in counts.items():
        b = _bits(k, n)
        l = tuple(b[:3])
        r = tuple(b[3:])
        pl[l] += v
        pr[r] += v
        pj[(l, r)] += v
    mi = 0.0
    for (l, r), v in pj.items():
        p = v / tot
        mi += p * np.log(p / (pl[l] / tot * pr[r] / tot))
    return float(mi)


def entropy_dist(counts):
    tot = sum(counts.values()) or 1
    return float(-sum(v / tot * np.log(v / tot) for v in counts.values()))

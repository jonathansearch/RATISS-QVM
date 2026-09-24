#!/usr/bin/env python3
"""S02 : COURBE DE PAGE — l'info revient-elle ? (CIBLE 1).
Reprend S01 (24 qubits, message 64 bits, 6 lois + Kuramoto) + évaporation
DÉCLARÉE : absorption t=0..30 (M=0.5), puis M 0.5->0.02 linéaire t=30..200
(pas Hawking exact, assumé), r_s(t)=2M. Qubit gelé avec r > r_s+0.05 :
RÉÉMIS (kick outward 1.5*v_esc, mécanisme déclaré ; le MESURÉ = F_info
et R, pas le kick). Observable Page : bits intacts DEHORS /64 : 1->0-> ?
Si -> ~0.79 (fidélité gelée S01) : l'info REVIENT (unitarité mesurée).
Si ~0 : rupture U. Contrôle : S01 (M const) reste à 0. T=10000, DT=0.02.
"""
import json
import os
import sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "organes"))
import conteneur as C

N, T, DT = 24, 10000, 0.02
EPS, KAPPA, KQ = 0.2, 0.2, 1.0
rng = np.random.default_rng(24)

r0 = np.concatenate([rng.uniform(2, 3.5, 12), rng.uniform(4, 6, 12)])
a0 = rng.uniform(0, 2 * np.pi, N)
X = np.column_stack([r0 * np.cos(a0), r0 * np.sin(a0),
                     rng.normal(0, 0.1, N)])
vc = np.sqrt(0.5 / r0) * 0.35
tang = np.column_stack([-np.sin(a0), np.cos(a0), np.zeros(N)])
V = tang * vc[:, None] - (X / r0[:, None]) * 0.05
th = rng.uniform(0, 2 * np.pi, N)
om = rng.normal(1.0, 0.05, N)
msg = np.tile([1, 1, 0, 0], 16).astype(np.uint8)
msg[:8] = [1, 0, 1, 0, 1, 0, 1, 0]
tranches = [msg[i::N].copy() for i in range(N)]
init = [t.copy() for t in tranches]
vifs = np.ones(N, bool)
temit = np.full(N, -1.0)


def M_of(t):
    if t < 30:
        return 0.5
    return max(0.02, 0.5 - (0.5 - 0.02) * (t - 30) / 170)


serie = []
for s in range(T + 1):
    t = s * DT
    M, rs = M_of(t), 2 * M_of(t)
    r = np.linalg.norm(X, axis=1)
    vifs[r < rs] = False
    # réémission : gelé mais dehors -> kick outward (déclaré)
    rev = (~vifs) & (r > rs + 0.05)
    if rev.any():
        vesc = np.sqrt(2 * M / r[rev])
        V[rev] = (X[rev] / r[rev][:, None]) * (1.5 * vesc)[:, None]
        vifs[rev] = True
        temit[rev & (temit < 0)] = t
    if s % 20 == 0:
        out = vifs
        agree = [np.mean(tranches[i] == init[i]) for i in range(N)]
        bits_out = sum((tranches[i] == init[i]).sum() for i in range(N)
                       if out[i])
        serie.append({"t": round(t, 1), "M": round(M, 4),
                      "rs": round(rs, 4), "n_out": int(out.sum()),
                      "bits_out": round(float(bits_out / 64), 4),
                      "F_frozen": round(float(np.mean(
                          [agree[i] for i in range(N) if not out[i]])
                          if (~out).any() else 1.0), 4),
                      "R_global": round(float(
                          np.abs(np.exp(1j * th).mean())), 4),
                      "r_moy": round(float(r.mean()), 3)})
    if s % 100 == 0:
        try:
            serie[-1]["P_sig"] = round(float(C.p_sig(X)), 4)
        except Exception:
            serie[-1]["P_sig"] = None
    if s == T:
        break
    rn = np.linalg.norm(X, axis=1)
    A = -M * X / (rn[:, None] ** 2 + EPS ** 2) ** 1.5
    V[vifs] += A[vifs] * DT
    X[vifs] += V[vifs] * DT
    rn = np.linalg.norm(X, axis=1)
    th[vifs] += om[vifs] * np.sqrt(np.maximum(0, 1 - rs / rn[vifs])) * DT
    th[vifs] += DT * (KQ / N) * np.sin(th - th[vifs][:, None]).sum(1)
    for i in range(N):
        if vifs[i] and rng.random() < KAPPA * DT / max(rn[i], rs):
            tranches[i][rng.integers(len(tranches[i]))] ^= 1
    if (s + 1) % 1000 == 0:
        print(f"[s02] t={t:.0f} M={M:.3f} rs={rs:.3f} dehors={vifs.sum()} "
              f"bits_out={serie[-1]['bits_out']}", flush=True)

emis = [{"qubit": i, "t_emit": round(float(temit[i]), 1),
         "F_tranche": round(float(np.mean(tranches[i] == init[i])), 3)}
        for i in range(N)]
json.dump({"serie": serie, "emission": emis,
           "config": {"loi7": "evaporation lineaire 0.5->0.02 (t 30..200)",
                      "emission": "kick 1.5*vesc (declare)"}},
          open(os.path.join(HERE, "..", "resultats", "s02.json"), "w"))
print(f"[s02] réémis={(temit >= 0).sum()}/24, bits_out_fin={serie[-1]['bits_out']}")

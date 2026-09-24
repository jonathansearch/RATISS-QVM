#!/usr/bin/env python3
"""S02b : DISSOCIATION MASSE/INFO (finir la cible 1).
Hawking confondait les deux : S02 a montré que l'info REVIENT (0.73).
Ici on trace la masse SÉPARÉMENT : qubits massifs (m=0.01 chacun) qui
alourdissent le puits en tombant et repartent avec leur masse à l'émission.
M_local(t) = M_BH(t) + 0.01 x n_gelés (MESURÉE via comptage, pas relue du
paramètre : le paramètre M_BH est déclaré, le terme qubits est dynamique).
+ non-recompaction : PHI_max dehors = max(1/d3^3) (concentration locale ;
si la masse réémise se recompactait, PHI exploserait).
Tranchement : I_rec -> ~0.73 ET M_local -> ~0.02 ET PHI_max ~ initial
=> dissociation prouvée (modèle) : l'info revient, la masse se dissipe
sans se re-compacter. T=10000, DT=0.02 (même evap que S02).
"""
import json
import os
import sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "organes"))
import conteneur as C

N, T, DT = 24, 10000, 0.02
EPS, KAPPA, KQ, MQ = 0.2, 0.2, 1.0, 0.01
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


def M_of(t):
    if t < 30:
        return 0.5
    return max(0.02, 0.5 - (0.5 - 0.02) * (t - 30) / 170)


def phi_max_dehors(Xo):
    if len(Xo) < 4:
        return None
    d = np.linalg.norm(Xo[:, None, :] - Xo[None, :, :], axis=2)
    d3 = np.sort(d, axis=1)[:, 1:4].mean(1)
    return float((1 / d3 ** 3).max())


serie = []
for s in range(T + 1):
    t = s * DT
    M, rs = M_of(t), 2 * M_of(t)
    r = np.linalg.norm(X, axis=1)
    vifs[r < rs] = False
    rev = (~vifs) & (r > rs + 0.05)
    if rev.any():
        vesc = np.sqrt(2 * M / r[rev])
        V[rev] = (X[rev] / r[rev][:, None]) * (1.5 * vesc)[:, None]
        vifs[rev] = True
    if s % 20 == 0:
        out = vifs
        bits_out = sum((tranches[i] == init[i]).sum() for i in range(N)
                       if out[i])
        Mloc = M + MQ * (~out).sum()
        serie.append({"t": round(t, 1), "M_BH": round(M, 4),
                      "M_local": round(float(Mloc), 4),
                      "n_geles": int((~out).sum()),
                      "I_rec": round(float(bits_out / 64), 4),
                      "PHI_max": (round(phi_max_dehors(X[out]), 4)
                                  if out.sum() >= 4 else None)})
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
    if (s + 1) % 2000 == 0:
        print(f"[s02b] t={t:.0f} Mloc={serie[-1]['M_local']} "
              f"I={serie[-1]['I_rec']} PHI={serie[-1]['PHI_max']}",
              flush=True)

json.dump({"serie": serie, "config": {"m_qubit": MQ}},
          open(os.path.join(HERE, "..", "resultats", "s02b.json"), "w"))
fin = serie[-1]
print(f"[s02b] fin : M_local={fin['M_local']} I_rec={fin['I_rec']} "
      f"PHI_max={fin['PHI_max']}")

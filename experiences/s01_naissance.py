#!/usr/bin/env python3
"""S01 : NAISSANCE D'UNE SINGULARITÉ 100 MASSES SOLAIRES + ABSORPTION.
Unités géométriques (G=c=1) : r_s = 2M = 1.0 = 295 km (100 M_sol).
6 lois ajoutées au socle focal (voir LOIS.md) : gravité -M/r² soft-core,
horizon r_s=1 (capture irréversible), redshift sqrt(1-rs/r), marée
diagnostiquée (pas imposée), fluctuations thermiques horizon T~1/r
(flips d'info), gel de l'info absorbée (choix assumé).
24 qubits à proximité (r 2-6 rs, sub-képlériens), phases-horloges,
message 64 bits en tranches disjointes (recette TEST-04 sans neurones).
On les laisse tomber. On observe TOUT : déformation, P_sig, intrication
universelle (R global + accord info), fluctuations, liaisons proximité,
gravité, relativité. T=2500, DT=0.02. Zéro verdict.
"""
import json
import os
import sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "organes"))
import conteneur as C

N, T, DT = 24, 2500, 0.02
MSIM, RS, EPS = 0.5, 1.0, 0.2
KAPPA, KQ = 0.2, 1.0
rng = np.random.default_rng(24)

# positions : moitié proche (2-3.5), moitié large (4-6)
r0 = np.concatenate([rng.uniform(2, 3.5, 12), rng.uniform(4, 6, 12)])
a0 = rng.uniform(0, 2 * np.pi, N)
X = np.column_stack([r0 * np.cos(a0), r0 * np.sin(a0),
                     rng.normal(0, 0.1, N)])
# vitesses sub-képlériennes (0.7 vcirc) + léger inward
vc = np.sqrt(MSIM / r0) * 0.35
tang = np.column_stack([-np.sin(a0), np.cos(a0), np.zeros(N)])
V = tang * vc[:, None] - (X / r0[:, None]) * 0.05
th = rng.uniform(0, 2 * np.pi, N)
om = rng.normal(1.0, 0.05, N)
# message 64 bits : marqueur + blocs, tranches entrelacées
msg = np.tile([1, 1, 0, 0], 16).astype(np.uint8)
msg[:8] = [1, 0, 1, 0, 1, 0, 1, 0]
tranches = [msg[i::N].copy() for i in range(N)]
init = [t.copy() for t in tranches]
vifs = np.ones(N, bool)
tabs = np.full(N, -1)
Xf = X.copy()

serie = []
snaps, snaps_t = [], []


def r_local(i, Xa, tha):
    d = np.linalg.norm(Xa - Xa[i], axis=1)
    vois = np.argsort(d)[1:4]
    return float(np.abs(np.exp(1j * tha[vois]).mean()))


for s in range(T + 1):
    r = np.linalg.norm(X, axis=1)
    # horizon : absorption
    new = vifs & (r < RS)
    tabs[new] = s * DT
    vifs[new] = False
    if s % 10 == 0:
        Xa, tha = X, th
        Rg = float(np.abs(np.exp(1j * tha).mean()))
        Rl = float(np.mean([r_local(i, Xa, tha) for i in range(N)]))
        acc = np.mean([np.mean(tranches[i] == init[i])
                       for i in range(N)])
        try:
            psig = round(float(C.p_sig(Xa)), 4)
        except Exception:
            psig = None
        act = Xa[vifs] if vifs.sum() > 3 else Xa
        cov = np.cov(act.T)
        lam = np.linalg.eigvalsh(cov + 1e-12 * np.eye(3))
        clock = float(np.mean(np.sqrt(np.maximum(0, 1 - RS / r))))
        acc_g = float(np.mean(MSIM / (r ** 2 + EPS ** 2)))
        vr = ((V * (X / r[:, None])).sum(1))
        serie.append({"t": round(s * DT, 2),
                      "r_moy": round(float(r.mean()), 4),
                      "n_abs": int((~vifs).sum()),
                      "R_global": round(Rg, 4), "R_local": round(Rl, 4),
                      "F_info": round(float(acc), 4), "P_sig": psig,
                      "deform": round(float(lam[2] / lam[0]), 3),
                      "clock": round(clock, 4),
                      "a_grav": round(acc_g, 4),
                      "fluct_v": round(float(vr.std()), 4),
                      "fluct_r": round(float(r.std()), 4)})
    if s in (0, 500, 1000, 1500):
        snaps.append([[round(float(v), 3) for v in row] for row in X])
        snaps_t.append(round(s * DT, 1))
    if s == T:
        break
    # gravité
    rn = np.linalg.norm(X, axis=1)
    A = -MSIM * X / (rn[:, None] ** 2 + EPS ** 2) ** 1.5
    V[vifs] += A[vifs] * DT
    X[vifs] += V[vifs] * DT
    # horloges redshiftées + couplage Q hérité (Kuramoto K=1)
    rn = np.linalg.norm(X, axis=1)
    th[vifs] += om[vifs] * np.sqrt(np.maximum(0, 1 - RS / rn[vifs])) * DT
    th[vifs] += DT * (KQ / N) * np.sin(th - th[vifs][:, None]).sum(1)
    # flips thermiques T~1/r
    for i in range(N):
        if vifs[i] and rng.random() < KAPPA * DT / max(rn[i], RS):
            tranches[i][rng.integers(len(tranches[i]))] ^= 1
    if (s + 1) % 500 == 0:
        print(f"[s01] t={(s+1)*DT:.0f} absorbés={(~vifs).sum()}/24 "
              f"r_moy={rn.mean():.2f} Rg={serie[-1]['R_global']} "
              f"F={serie[-1]['F_info']}", flush=True)

absorp = [{"qubit": i, "t_abs": round(float(tabs[i]), 2),
           "F_tranche": round(float(np.mean(tranches[i] == init[i])), 3)}
          for i in range(N)]
json.dump({"serie": serie, "absorption": absorp,
           "snaps": snaps, "snaps_t": snaps_t,
           "config": {"N": N, "T": T, "DT": DT, "M_sim": MSIM, "r_s": RS,
                      "M_phys": "100 M_sol", "r_s_km": 295}},
          open(os.path.join(HERE, "..", "resultats", "s01.json"), "w"))
print(f"[s01] absorbés={(tabs >= 0).sum()}/24, archivé.")

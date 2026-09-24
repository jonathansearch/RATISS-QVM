"""S06b v2 — MESSAGERS + ENROULEMENT (MISSION 5b)
V1 : mécanisme OK (909 vs 170 msg) mais critère E_proxy<0 CASSÉ (balistique
lente = faussement liée ; chauffage stochastique = faussement libre).
V2 : critère ENROULEMENT — retenue si |Δθ|>π (a tourné autour du fantôme ;
une balistique file droit, Δθ<π). E_proxy gardé pour comparaison.
DECLARE : cf. v1 (RHO=0.05, TAU=1500, SIGMA=0.25, R_PULL=0.6, scan KAP,
M_EFF=0.12 pour E_proxy, tore L=6 vs fuite à r>L, pommes libres).
MESURE : n_retenues_wind FERME vs OUVERT par KAP = effet de la fermeture.
"""
import json
import numpy as np
from ripser import ripser

T, DT = 2500, 0.02
MSIM, RS, EPS = 0.5, 1.0, 0.2
N1, N2 = 12, 12
L = 6.0
RHO = 0.05
TAU = 1500
SIGMA = 0.25
R_PULL = 0.6
KAPS = [3e-5, 7e-5, 1.5e-4]
M_EFF = 0.12
M_CAP = 6000


def pommes(seed):
    rng = np.random.default_rng(seed)
    r0 = np.concatenate([rng.uniform(2, 3.5, 6), rng.uniform(4, 6, 6)])
    a0 = rng.uniform(0, 2 * np.pi, N2)
    X = np.column_stack([r0 * np.cos(a0), r0 * np.sin(a0)])
    vc = np.sqrt(MSIM / r0) * 0.35
    tang = np.column_stack([-np.sin(a0), np.cos(a0)])
    V = tang * vc[:, None] - (X / r0[:, None]) * 0.05
    return X, V


def h1_of(X):
    return max([float(b[1] - b[0])
                for b in ripser(X)['dgms'][1]] or [0.0])


X1, V1 = pommes(41)
vifs = np.ones(N1, bool)
for s in range(T + 1):
    r = np.linalg.norm(X1, axis=1)
    vifs[r < RS] = False
    rr1 = np.linalg.norm(X1[vifs], axis=1, keepdims=True)
    V1[vifs] += (-MSIM * X1[vifs] / (rr1 ** 2 + EPS ** 2) ** 1.5) * DT
    X1[vifs] += V1[vifs] * DT
shell = X1[~vifs]
print(f"[s06b] passé : {len(shell)}/{N1} gobés (empreinte source)")


def run(clos, kap):
    Xa, Va = pommes(42)
    rngM = np.random.default_rng(77)
    Mp = np.zeros((0, 2))
    Ms = np.zeros((0, 2))
    Mage = np.zeros(0)
    th_prev = np.arctan2(Xa[:, 1], Xa[:, 0])
    wind = np.zeros(N2)               # enroulement cumulé (le détecteur !)
    serie = []
    for s in range(T + 1):
        n_new = rngM.poisson(len(shell) * RHO)
        if n_new > 0:
            src = shell[rngM.integers(0, len(shell), n_new)]
            Mp = np.vstack([Mp, src + rngM.normal(0, 0.05, (n_new, 2))])
            Ms = np.vstack([Ms, src])
            Mage = np.concatenate([Mage, np.zeros(n_new)])
        if len(Mp) > M_CAP:
            Mp, Ms, Mage = Mp[:M_CAP], Ms[:M_CAP], Mage[:M_CAP]
        Mage += 1
        Mp += rngM.normal(0, SIGMA, Mp.shape)
        if clos:
            Mp = ((Mp + L) % (2 * L)) - L
        else:
            keep = np.linalg.norm(Mp, axis=1) <= L
            Mp, Ms, Mage = Mp[keep], Ms[keep], Mage[keep]
        keep_age = Mage <= TAU
        Mp, Ms, Mage = Mp[keep_age], Ms[keep_age], Mage[keep_age]
        if len(Mp):
            dd = Xa[:, None, :] - Mp[None, :, :]
            dist = np.sqrt((dd ** 2).sum(-1))
            for i in range(N2):
                hits = dist[i] < R_PULL
                if hits.any():
                    u = Ms[hits] - Xa[i]
                    u /= np.maximum(np.linalg.norm(u, axis=1,
                                                   keepdims=True), 1e-9)
                    Va[i] += kap * u.sum(0)
        Xa += Va * DT
        th = np.arctan2(Xa[:, 1], Xa[:, 0])
        wind += (th - th_prev + np.pi) % (2 * np.pi) - np.pi
        th_prev = th
        if s % 250 == 0:
            serie.append({'t': round(s * DT, 2), 'n_msg': int(len(Mp)),
                          'r_moy': float(np.linalg.norm(Xa, axis=1).mean()),
                          'H1': h1_of(Xa)})
    rf = np.linalg.norm(Xa, axis=1)
    E = (Va ** 2).sum(1) / 2 - M_EFF / np.maximum(rf, 1e-9)
    return {'n_wind': int((np.abs(wind) > np.pi).sum()),
            'n_E': int((E < 0).sum()),
            'wind_moy': float(np.abs(wind).mean()),
            'n_msg_fin': int(len(Mp)), 'rfinal_moy': float(rf.mean()),
            'H1_fin': serie[-1]['H1'], 'serie': serie}


out = {}
for kap in KAPS:
    for clos in [True, False]:
        nom = f"{'FERME' if clos else 'OUVERT'}-k{kap:g}"
        out[nom] = run(clos, kap)
        r = out[nom]
        print(f"[s06b] {nom:14s} : WIND={r['n_wind']:2d}/12 "
              f"(E:{r['n_E']:2d}) msg={r['n_msg_fin']:4d} "
              f"rfin={r['rfinal_moy']:.2f} H1={r['H1_fin']:.3f}")

json.dump({'params_declares': {'T': T, 'DT': DT, 'L': L, 'RHO': RHO,
                               'TAU': TAU, 'SIGMA': SIGMA,
                               'R_PULL': R_PULL, 'KAPS': KAPS,
                               'M_EFF': M_EFF},
           'runs': out},
          open('resultats/s06b.json', 'w'))
print('[s06b] enroulements mesurés, fermeture jugée 🌀⚖️')

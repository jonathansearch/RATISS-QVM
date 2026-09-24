"""S05 — FANTÔME : les trous gravitent-ils sans matière ? (MISSION 4)
CIBLE 4 du PROGRAMME §4.4 : "masses absorbées retirées, empreinte H1 gardée
-> la chute des suivants change-t-elle ?" Oui = gravité sans matière
(mémoire topologique) ; non = la topologie seule ne pèse pas.
DECLARE : passé COMMUN (batch-1 : 12 qubits recette S01 2D gobés par M=0.5,
  gelés loi-6, masse 0.01 chacun loi-S02b = l'EMPREINTE) ; puis 3 présents :
  VIDE (M=0, pas d'empreinte), FANTOME (M=0 + empreinte), TROU (M=0.5 +
  empreinte). Batch-2 : 12 pommes, recette S01, seed IDENTIQUE (appariées !).
  Micro-loi : central M_res (soft 0.2) + paires coquille/b ajoutées (0.01,
  soft 0.05). Gel (r<1) seulement si M_res>0 (pas d'horizon sans masse !).
MESURE : batch-2 retenu ou enfui ? n_liés (E<0), r_min, r_final, H1_2(t),
  H1_empreinte. FANTOME vs VIDE (même M=0 !) = effet pur de l'empreinte.
"""
import json
import numpy as np
from ripser import ripser

T, DT = 2500, 0.02      # S01-identique (t=50)
MSIM, RS, EPS = 0.5, 1.0, 0.2
M_QUBIT, EPS2 = 0.01, 0.05
N1, N2 = 12, 12


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


def accel(X, M_res, shell):
    rr = np.linalg.norm(X, axis=1, keepdims=True)
    a = -M_res * X / (rr ** 2 + EPS ** 2) ** 1.5   # central soft-core S01
    for src in ([shell] if shell is not None else []) + [X]:
        d = X[:, None, :] - src[None, :, :]
        rr = np.sqrt((d ** 2).sum(-1)) + np.eye(len(X), len(src))
        rr = np.maximum(rr, EPS2)
        f = (-M_QUBIT / rr ** 3)[..., None]
        if src is X:
            np.fill_diagonal(f[:, :, 0], 0.0)
        a += (d * f).sum(1)
    return a


# ---- passé commun : batch-1 absorbé -> EMPREINTE ----
X1, V1 = pommes(41)
vifs = np.ones(N1, bool)
for s in range(T + 1):
    r = np.linalg.norm(X1, axis=1)
    vifs[r < RS] = False
    V1[vifs] += accel(X1[vifs], MSIM, None) * DT
    X1[vifs] += V1[vifs] * DT
shell = X1[~vifs]                       # positions gelées = l'empreinte
M_ghost = M_QUBIT * len(shell)
H1_shell = h1_of(shell) if len(shell) > 3 else 0.0
print(f"[s05] passé : {len(shell)}/{N1} gobés, M_fantôme={M_ghost:.2f}, "
      f"H1_empreinte={H1_shell:.3f}")


def run(nom, M_res, use_shell):
    X, V = pommes(42)                   # LES MÊMES pommes partout !
    vifs2 = np.ones(N2, bool)
    rmin = np.full(N2, 1e9)
    serie = []
    sh = shell if use_shell else None
    for s in range(T + 1):
        r = np.linalg.norm(X, axis=1)
        rmin[vifs2] = np.minimum(rmin[vifs2], r[vifs2])
        if M_res > 0:
            vifs2[r < RS] = False       # horizon = seulement avec masse
        if s % 250 == 0:
            serie.append({'t': round(s * DT, 2),
                          'n_vifs': int(vifs2.sum()),
                          'r_moy': float(r[vifs2].mean()) if vifs2.any()
                          else 0.0,
                          'H1': h1_of(X[vifs2]) if vifs2.sum() > 3 else 0.0})
        V[vifs2] += accel(X[vifs2], M_res, sh) * DT
        X[vifs2] += V[vifs2] * DT
    rf = np.linalg.norm(X, axis=1)
    vv = (V ** 2).sum(1)
    M_cent = (M_res if M_res > 0 else 0.0) + (M_ghost if use_shell else 0.0)
    E = vv / 2 - M_cent / np.maximum(rf, 1e-9)
    n_lies = int(((E < 0) | ~vifs2).sum()) if M_cent > 0 else 0
    return {'n_gobes': int((~vifs2).sum()), 'n_lies': n_lies,
            'rmin_moy': float(rmin.mean()), 'rfinal_moy': float(rf.mean()),
            'H1_fin': serie[-1]['H1'], 'serie': serie}


out = {}
for nom, M_res, sh in [('VIDE', 0.0, False), ('FANTOME', 0.0, True),
                       ('TROU', MSIM, True)]:
    out[nom] = run(nom, M_res, sh)
    r = out[nom]
    print(f"[s05] {nom:7s} : gobés={r['n_gobes']:2d}/12 liés={r['n_lies']:2d}/12 "
          f"rmin={r['rmin_moy']:.2f} rfinal={r['rfinal_moy']:.2f} "
          f"H1_fin={r['H1_fin']:.3f}")

json.dump({'params_declares': {'T': T, 'DT': DT, 'MSIM': MSIM, 'RS': RS,
                               'EPS': EPS, 'M_QUBIT': M_QUBIT,
                               'n_empreinte': len(shell),
                               'M_ghost': M_ghost,
                               'H1_empreinte': H1_shell},
           'runs': out},
          open('resultats/s05.json', 'w'))
print('[s05] chasse au fantôme terminée 👻🍎')

"""S06a — BORD OUVERT : le fantôme-lien craint-il le vide ? (MISSION 5a)
Ordre chef (suggestion Qwen) : reprendre S05-FANTOME dans un univers OUVERT
(bord absorbant) -> les pommes fuient-elles (0/12) malgré l'empreinte ?
DECLARE : phase-0 S05 identique (shell seed 41, M=0.5, 12/12 gobés) ;
  FANTOME-OUVERT : M=0 + empreinte + pommes seed 42 + bord absorbant
  R_OUT=8 (apocentres liés <~6 : le bord ne mange que les vrais évadés,
  vérifié par E>0 à la sortie). Micro-loi paire-à-paire INCHANGÉE.
  + contrôle VIDE-OUVERT (le bord mange-t-il bien les fuyards ?).
MESURE : n_retenues (E<0) vs S05-fermé 9/12.
  PRÉDIT (honnête) : 9/12 INCHANGÉ -> la gravité-LIEN ignore la topologie
  (Newton ne sait pas si le monde est ouvert). Réfutation de l'hypothèse
  naïve = physique CORRECTE pour l'action à distance. La chance de
  l'hypothèse = S06b (gravité-CHAMP par messagers qui fuient).
"""
import json
import numpy as np
from ripser import ripser

T, DT = 2500, 0.02
MSIM, RS, EPS = 0.5, 1.0, 0.2
M_QUBIT, EPS2 = 0.01, 0.05
N1, N2 = 12, 12
R_OUT = 8.0           # bord du monde ouvert (déclaré)


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


def accel(X, shell):
    rr = np.linalg.norm(X, axis=1, keepdims=True)
    a = np.zeros_like(X)              # M=0 : pas de centre, que les liens
    for src in ([shell] if shell is not None else []) + [X]:
        d = X[:, None, :] - src[None, :, :]
        dd = np.sqrt((d ** 2).sum(-1)) + np.eye(len(X), len(src))
        dd = np.maximum(dd, EPS2)
        f = (-M_QUBIT / dd ** 3)[..., None]
        if src is X:
            np.fill_diagonal(f[:, :, 0], 0.0)
        a += (d * f).sum(1)
    return a


X1, V1 = pommes(41)                   # passé commun S05
vifs = np.ones(N1, bool)
for s in range(T + 1):
    r = np.linalg.norm(X1, axis=1)
    vifs[r < RS] = False
    rr1 = np.linalg.norm(X1[vifs], axis=1, keepdims=True)
    V1[vifs] += (-MSIM * X1[vifs] / (rr1 ** 2 + EPS ** 2) ** 1.5) * DT
    X1[vifs] += V1[vifs] * DT
shell = X1[~vifs]
M_ghost = M_QUBIT * len(shell)
print(f"[s06a] passé : {len(shell)}/{N1} gobés, M_fantôme={M_ghost:.2f}")


def run(nom, use_shell):
    X, V = pommes(42)
    vifs2 = np.ones(N2, bool)
    enfuies, E_out = np.zeros(N2, bool), []
    serie = []
    sh = shell if use_shell else None
    M_cent = M_ghost if use_shell else 1e-12
    for s in range(T + 1):
        r = np.linalg.norm(X, axis=1)
        out = vifs2 & (r > R_OUT)     # le bord mange les fuyards
        if out.any():
            vv = (V[out] ** 2).sum(1)
            E_out.extend((vv / 2 - M_cent / r[out]).tolist())
            enfuies[out] = True
            vifs2[out] = False
        if s % 250 == 0:
            serie.append({'t': round(s * DT, 2),
                          'n_presentes': int(vifs2.sum()),
                          'H1': h1_of(X[vifs2]) if vifs2.sum() > 3 else 0.0})
        V[vifs2] += accel(X[vifs2], sh) * DT
        X[vifs2] += V[vifs2] * DT
    rf = np.linalg.norm(X, axis=1)
    E = (V ** 2).sum(1) / 2 - M_cent / np.maximum(rf, 1e-9)
    n_retenues = int(((E < 0) & vifs2).sum())
    return {'n_retenues': n_retenues, 'n_enfuies': int(enfuies.sum()),
            'E_sortie_moy': float(np.mean(E_out)) if E_out else None,
            'E_sortie_list': [float(e) for e in E_out],
            'H1_fin': serie[-1]['H1'], 'serie': serie}


out = {}
for nom, sh in [('VIDE-OUVERT', False), ('FANTOME-OUVERT', True)]:
    out[nom] = run(nom, sh)
    r = out[nom]
    print(f"[s06a] {nom:13s} : retenues={r['n_retenues']:2d}/12 "
          f"enfuies={r['n_enfuies']:2d}/12 E_sortie={r['E_sortie_moy']} "
          f"H1_fin={r['H1_fin']:.3f} (S05-fermé : 9/12)")

json.dump({'params_declares': {'T': T, 'DT': DT, 'R_OUT': R_OUT,
                               'M_ghost': M_ghost},
           'runs': out},
          open('resultats/s06a.json', 'w'))
print('[s06a] bord testé, verdict sec 🧱')

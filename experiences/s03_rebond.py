"""S03 — Rebond de Planck vs effondrement GR : l'anneau survit-il ?
MISSION 2 / CIBLE 2 du PROGRAMME : "l'univers rebondit-il ?"

DECLARE (micro-loi, honnête) : force par paires F = -g/r^2 + k/r^4
  (attraction + coeur répulsif type Lennard-Jones). k=0 -> GR-like ;
  k>0 -> Planck-like, avec r_eq = sqrt(k/g) et rho_crit déclarée.
  + friction GAMMA (relaxation violente) : SANS elle les particules
  restent en orbite (centrifuge, cf. S01) et le régime dense n'est
  jamais atteint (v1 : rho_max < rho_crit, combat annulé).
  Le point de chute N'EST PAS codé : il doit ÉMERGER (ou pas).
MESURE : r_rms(t), rho(t), et surtout H1(t) (ripser, module déclaré)
  d'un anneau initial (tatouage H1 ~ R0) :
  H1 fini + r~r_eq + rho~rho_crit = REBOND (structure survit, NON-DÉBUT) ;
  H1->0 + r->plancher + rho->infini = EFFONDREMENT (GR pulvérise tout).
"""
import json
import numpy as np
from ripser import ripser

N = 24          # les 24 gladiateurs
T = 1600        # pas de temps
DT = 0.01
G = 0.3         # attraction déclarée
GAMMA = 0.5     # boue sur la piste (friction déclarée)
R_EQ = 0.6      # échelle Planck-like déclarée -> k = G*R_EQ^2
K = G * R_EQ ** 2
R0 = 4.0        # rayon initial de l'anneau
R_NUM = 0.05    # plancher numérique déclaré (anti-infini)
RHO_CRIT = N / (4 / 3 * np.pi * R_EQ ** 3)  # ~26.5, déclarée
rng = np.random.default_rng(3)


def run(k):
    th = np.linspace(0, 2 * np.pi, N, endpoint=False)
    pos = np.stack([R0 * np.cos(th), R0 * np.sin(th)], 1)
    pos += rng.normal(0, 0.05, pos.shape)  # imperfection réaliste
    rr = np.linalg.norm(pos, axis=1, keepdims=True)
    vel = -1.0 * pos / rr + rng.normal(0, 0.02, pos.shape)  # charge !
    serie = []
    for step in range(T + 1):
        if step % 40 == 0:
            rr = np.linalg.norm(pos, axis=1)
            r_rms = float(np.sqrt((rr ** 2).mean()))
            rho = float(N / (4 / 3 * np.pi * r_rms ** 3))
            h1 = max([float(b[1] - b[0])
                      for b in ripser(pos)['dgms'][1]] or [0.0])
            vr = float(((vel * pos).sum(1) / np.maximum(rr, 1e-9)).mean())
            serie.append({'t': round(step * DT, 2), 'r_rms': r_rms,
                          'rho': rho, 'H1': h1, 'vr': vr})
        d = pos[:, None, :] - pos[None, :, :]          # vecteurs paires
        r = np.sqrt((d ** 2).sum(-1)) + np.eye(N)      # diag=1, F_ii=0
        r = np.maximum(r, R_NUM)
        f = (-G / r ** 3 + k / r ** 5)[..., None]      # micro-loi
        vel += (d * f).sum(1) * DT
        vel *= (1 - GAMMA * DT)                        # la boue !
        pos += vel * DT
    return serie


out = {}
for nom, k in [('GR', 0.0), ('Planck', K)]:
    s = run(k)
    h1_0 = s[0]['H1']
    out[nom] = {
        'serie': s,
        'H1_init': h1_0,
        'H1_fin': s[-1]['H1'],
        'retour_H1': s[-1]['H1'] / h1_0 if h1_0 else 0,
        'r_min': min(r['r_rms'] for r in s),
        'r_fin': s[-1]['r_rms'],
        'rho_max': max(r['rho'] for r in s),
        'rho_fin': s[-1]['rho'],
    }
    print(f"[s03] {nom} : H1 {h1_0:.2f} -> {s[-1]['H1']:.3f} "
          f"(retour {out[nom]['retour_H1']:.3f}), "
          f"r {R0} -> {s[-1]['r_rms']:.3f}, "
          f"rho_fin={s[-1]['rho']:.1f} (rho_crit={RHO_CRIT:.1f})")

json.dump({'params_declares': {'N': N, 'T': T, 'DT': DT, 'G': G,
                               'GAMMA': GAMMA, 'K': K, 'R_EQ': R_EQ,
                               'R0': R0, 'RHO_CRIT': RHO_CRIT},
           'runs': out},
          open('resultats/s03.json', 'w'))
print('[s03] combat rapproché terminé, JSON scellé 🥊')

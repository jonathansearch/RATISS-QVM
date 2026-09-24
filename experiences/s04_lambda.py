"""S04 — LAMBDA v3 : séparatrice fine + course mémoire (MISSION 3)
CIBLE 3 du PROGRAMME §4.3 : "quelle répulsion effective stabilise Φ ?"
+ vision POIDS (concentration gravitationnelle spontanée).

V1 ÉCHOUÉE : pas de CRUNCH (rate le centre), fragmentation partout, RIP
dès 0.06 (crayon 0.1125 réfuté). V2 : séparatrice LIÉ/LIBRE entre 0.015
et 0.02 MAIS les "LIÉ" 0.005-0.015 accéléraient encore à t=60 = TIME-OUTS.
V3 : t=120 + Lambda=0.002 pour la VRAIE séparatrice.
DECLARE : attraction -g/r^2, F_Lambda=+Lambda.r, γ=0.3, anneau R0=4.
MESURE : Lambda* (vrai), signe, ordre de grandeur, course H1 (l'expansion
  rapide fige l'anneau : H1 gonfle ; lente : fragmentation, H1 meurt).
"""
import json
import numpy as np
from ripser import ripser

N = 24
T = 12000         # t=120 : les ultra-lents tranchent aussi
DT = 0.01
G = 0.3
GAMMA = 0.3
R0 = 4.0
R_NUM = 0.05
R_RIP = 30.0
R_CRUNCH = 0.15
LAMBDAS = [-0.05, 0.0, 0.002, 0.005, 0.01, 0.015, 0.02, 0.03,
           0.045, 0.06, 0.09, 0.13, 0.2]
rng = np.random.default_rng(11)


def snapshot(pos, step):
    rr = np.linalg.norm(pos, axis=1)
    r_rms = float(np.sqrt((rr ** 2).mean()))
    rho = float(N / (4 / 3 * np.pi * r_rms ** 3))
    h1 = max([float(b[1] - b[0])
              for b in ripser(pos)['dgms'][1]] or [0.0])
    dd = np.sqrt(((pos[:, None, :] - pos[None, :, :]) ** 2).sum(-1))
    dd += np.eye(N) * 1e9
    return {'t': round(step * DT, 2), 'r_rms': r_rms, 'rho': rho,
            'H1': h1, 'd_min': float(dd.min())}


def run(lam):
    th = np.linspace(0, 2 * np.pi, N, endpoint=False)
    pos = np.stack([R0 * np.cos(th), R0 * np.sin(th)], 1)
    pos += rng.normal(0, 0.05, pos.shape)
    vel = rng.normal(0, 0.02, pos.shape)
    serie = [snapshot(pos, 0)]
    fate, t_fate = 'LIE', T * DT
    for step in range(1, T + 1):
        d = pos[:, None, :] - pos[None, :, :]
        r = np.sqrt((d ** 2).sum(-1)) + np.eye(N)
        r = np.maximum(r, R_NUM)
        f = (-G / r ** 3)[..., None]
        vel += (d * f).sum(1) * DT
        vel += lam * pos * DT                 # LE FANTÔME 👻
        vel *= (1 - GAMMA * DT)
        pos += vel * DT
        r_rms = float(np.sqrt((pos ** 2).sum(1).mean()))
        if r_rms > R_RIP:
            fate, t_fate = 'RIP', step * DT
            serie.append(snapshot(pos, step))
            break
        if r_rms < R_CRUNCH:
            fate, t_fate = 'CRUNCH', step * DT
            serie.append(snapshot(pos, step))
            break
        if step % 400 == 0:
            serie.append(snapshot(pos, step))
    return {'fate': fate, 't_fate': t_fate, 'serie': serie}


out = {}
for lam in LAMBDAS:
    out[str(lam)] = run(lam)
    r = out[str(lam)]
    print(f"[s04] Lambda={lam:+.3f} : {r['fate']:6s} à t={r['t_fate']:6.1f} "
          f"(H1 fin={r['serie'][-1]['H1']:.3f}, "
          f"r fin={r['serie'][-1]['r_rms']:.2f})")

lies = [l for l in LAMBDAS if out[str(l)]['fate'] == 'LIE']
rips = [l for l in LAMBDAS if out[str(l)]['fate'] == 'RIP']
print(f"[s04] VRAIE séparatrice : entre {max(lies) if lies else '?'} "
      f"(dernier LIÉ) et {min(rips) if rips else '?'} (premier RIP)")
json.dump({'params_declares': {'N': N, 'T': T, 'DT': DT, 'G': G,
                               'GAMMA': GAMMA, 'R0': R0, 'R_RIP': R_RIP,
                               'R_CRUNCH': R_CRUNCH, 'LAMBDAS': LAMBDAS},
           'runs': out},
          open('resultats/s04.json', 'w'))
print('[s04] fantôme cloué au mur 👻🔨')

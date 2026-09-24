"""S03b — RÉSURRECTION : le Big Bang arrive-t-il ? (match retour S03)
MISSION 2b : "si tout prend la même position" (point zéro) puis on lâche :
  le Big Bang arrive-t-il ? Comment ça se réorganise ? Les qubits existent-ils
  encore une fois mesurés ? Quelles dimensions à la résurrection ?
DECLARE : point zéro (boule eps=0.1, quasi-ponctuelle, 40x plus petite que
  l'anneau S03), micro-loi S03 INCHANGÉE (F=-g/r^2+k/r^4, mêmes g,k),
  SANS friction (univers libre), bits initiaux alternés + flip au contact
  (voisin < 0.3 : flip avec p=0.1/pas, seed fixe).
MESURE : r(t) (Bang ou pas), H1(t) (structure émergente 0->?), loi de Hubble
  v=H.r (H.t~1 = flot balistique), rondeur (12 secteurs angulaires),
  24/24 bits lisibles + motif F(t), d_min (pas de fusion), rho(t).
"""
import json
import numpy as np
from ripser import ripser

N = 24            # les 24 rescapés du point zéro
T = 4000          # pas (dt fin : le Bang, c'est violent)
DT = 0.002
G = 0.3           # mêmes constantes que S03 (comparaison honnête)
K = G * 0.6 ** 2
EPS = 0.1         # le "point" (quasi-ponctuel, pas singulier-numérique)
R_NUM = 0.05      # plancher déclaré
R_FLIP = 0.3      # contact qui flippe les bits (déclaré)
P_FLIP = 0.1
rng = np.random.default_rng(7)


def run(k):
    pos = rng.normal(0, EPS, (N, 2))
    vel = rng.normal(0, 1e-3, (N, 2))
    bits = np.arange(N) % 2
    init = bits.copy()
    serie = []
    for step in range(T + 1):
        if step % 100 == 0:
            rr = np.linalg.norm(pos, axis=1)
            r_rms = float(np.sqrt((rr ** 2).mean()))
            r_max = float(rr.max())
            rho = float(N / (4 / 3 * np.pi * r_rms ** 3))
            dg = ripser(pos)['dgms'][1]
            pers = sorted([float(b[1] - b[0]) for b in dg], reverse=True)
            h1max = pers[0] if pers else 0.0
            vr = (vel * pos / np.maximum(rr, 1e-9)[:, None]).sum(1)
            # Hubble : pente vr vs r (flot balistique -> H.t ~ 1)
            H = float(np.polyfit(rr, vr, 1)[0]) if r_rms > 0.2 else 0.0
            F = float((bits == init).mean())
            dd = np.sqrt(((pos[:, None, :] - pos[None, :, :]) ** 2).sum(-1))
            dd += np.eye(N) * 1e9
            ang = np.arctan2(pos[:, 1], pos[:, 0])
            sectors = int(len(set((((ang + np.pi) / (2 * np.pi) * 12)
                                     .astype(int)) % 12)))
            serie.append({'t': round(step * DT, 2), 'r_rms': r_rms,
                          'r_max': r_max, 'rho': rho, 'H1': h1max,
                          'H': H, 'F': F, 'd_min': float(dd.min()),
                          'secteurs': sectors})
        d = pos[:, None, :] - pos[None, :, :]
        r = np.sqrt((d ** 2).sum(-1)) + np.eye(N)
        r = np.maximum(r, R_NUM)
        f = (-G / r ** 3 + k / r ** 5)[..., None]   # micro-loi S03
        vel += (d * f).sum(1) * DT
        pos += vel * DT
        close = (r < R_FLIP) & (~np.eye(N, dtype=bool))
        flips = (rng.random((N, N)) < P_FLIP) & close
        bits ^= (flips.any(0) | flips.any(1)).astype(int)
    return serie


out = {}
for nom, k in [('GR', 0.0), ('Planck', K)]:
    s = run(k)
    fin = s[-1]
    out[nom] = {'serie': s, 'fin': fin, 'H_t': fin['H'] * fin['t'],
                'bits_lisibles': N}
    print(f"[s03b] {nom} : r 0.1 -> {fin['r_rms']:.2f}, H1 {s[0]['H1']:.3f} "
          f"-> {fin['H1']:.2f}, H.t={fin['H'] * fin['t']:.2f}, "
          f"F={fin['F']:.2f}, secteurs={fin['secteurs']}/12, "
          f"d_min={fin['d_min']:.4f}, rho={fin['rho']:.2e}")

json.dump({'params_declares': {'N': N, 'T': T, 'DT': DT, 'G': G, 'K': K,
                               'EPS': EPS, 'R_FLIP': R_FLIP,
                               'P_FLIP': P_FLIP},
           'runs': out},
          open('resultats/s03b.json', 'w'))
print('[s03b] résurrection terminée, que les meilleurs gagnent 🕊️')

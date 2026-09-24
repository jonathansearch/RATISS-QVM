"""L'EFFET : 12 paires de Bell à cheval sur l'horizon, N=300, évaporation S02.
L'intrication MEURT à la chute et RESSUSCITE à la réémission (Page quantique).
Portes appliquées EN DIRECT dans l'univers. Sortie : effet_horizon.gif. MIT."""
import sys
sys.path.insert(0, '/home/user/RATISS-QVM')
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from rqvm.universe import Universe, M_of

NV = sys.argv[sys.argv.index('--nv') + 1] if '--nv' in sys.argv else 'naturel'
T2 = 1.0 if NV == 'purifie' else 1.0e-3
U = Universe(n=300, evap=True, seed=24, nv_t2_300k=T2)
print(f'[effet] NV diamant: {NV} (kh_nv={U.kh_nv:.4f})', flush=True)

r0 = np.linalg.norm(U.X, axis=1)
inners = np.where(r0 < 3.0)[0][:12]
outers = np.where(r0 > 4.5)[0][:12]
# PLONGÉE SYNCHRO : coquille r=2.5, même vitesse (dip+revival cohérents)
for k, q in enumerate(inners):
    ang = 2 * np.pi * k / 12
    U.X[q] = np.array([2.5 * np.cos(ang), 2.5 * np.sin(ang), 0.0])
    U.V[q] = -U.X[q] / 2.5 * 0.05
# GUETTEURS : orbites circulaires stables (jamais absorbés) ; PLONGEURS : chutent
for q in outers:
    r = max(np.linalg.norm(U.X[q]), 0.5)
    t = np.array([-U.X[q, 1], U.X[q, 0], 0.0]) / r
    U.V[q] = t * np.sqrt(0.5 / r)
for a, b in zip(inners, outers):
    U.bell(int(a), int(b))
paired = set(int(x) for x in list(inners) + list(outers))
free = [i for i in range(300) if i not in paired][:6]
for q in free:
    U.gate('h', q)  # superposition live sur qubits libres
print(f'[effet] 12 paires Bell créées : inner={list(inners)}', flush=True)

STEPS, SHOT = 10000, 200
snaps, series = [], []
for s in range(STEPS + 1):
    if s == 4000:  # manipulation EN DIRECT : X sur les qubits libres
        for q in free:
            if q not in U.pairs:
                U.gate('x', q)
        print('[effet] t=80 : le chef flippe les qubits libres', flush=True)
    if s % SHOT == 0:
        rs = 2 * M_of(U.t, True)
        cs = [U.concurrence(int(a)) for a in inners]
        tot = sum(len(t) for t in U.tranches)
        out = sum(np.mean(U.tranches[i] == U.init[i]) * len(U.tranches[i])
                  for i in np.where(U.vifs)[0])
        snaps.append({'X': U.X[:, :2].copy(), 'vifs': U.vifs.copy(), 'rs': rs,
                      'C': cs, 't': U.t, 'F': U.f_info(), 'P': out / tot})
        series.append({'t': round(U.t, 1), 'Cmean': round(float(np.mean(cs)), 4),
                       'F': round(U.f_info(), 4), 'P': round(snaps[-1]['P'], 4),
                       'n_abs': int((~U.vifs).sum())})
    if s == STEPS:
        break
    U.step()
json.dump(series, open('/home/user/RATISS-QVM/demos/effet_horizon.json', 'w'))
cs = np.array([p['Cmean'] for p in series])
print(f"[effet] C: 1.0 -> min={cs.min():.3f} -> fin={cs[-1]:.3f} | F: {series[0]['F']} -> {min(p['F'] for p in series):.3f} -> {series[-1]['F']}")
from rqvm.qsubstrate import measure_1q
print('[effet] mesure Born qubits libres:', [measure_1q(U.psi[q], U.rng) for q in free])

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 3.4), dpi=80)
NF = len(snaps)


def frame(i):
    ax1.clear()
    ax2.clear()
    sn = snaps[i]
    X, v = sn['X'], sn['vifs']
    ax1.scatter(X[v, 0], X[v, 1], c='steelblue', s=4)
    ax1.scatter(X[~v, 0], X[~v, 1], c='black', s=6)
    for (a, b), c in zip(zip(inners, outers), sn['C']):
        col = 'limegreen' if c > 0.5 else ('orange' if c > 0.2 else 'red')
        ax1.plot([X[a, 0], X[b, 0]], [X[a, 1], X[b, 1]], color=col, lw=1, alpha=0.8)
    ax1.add_patch(plt.Circle((0, 0), sn['rs'], color='black', alpha=0.85))
    ax1.set_xlim(-7, 7)
    ax1.set_ylim(-7, 7)
    ax1.set_aspect('equal')
    ax1.set_title(f"Univers 300q — t={sn['t']:.0f} (NV {NV})")
    ts = [p['t'] for p in series[:i + 1]]
    for j in range(12):
        ax2.plot(ts, [snaps[k]['C'][j] for k in range(i + 1)], color='green',
                 lw=0.5, alpha=0.5)
    ax2.plot(ts, [p['Cmean'] for p in series[:i + 1]], 'g-', lw=2,
             label='C moyen (12 paires)')
    ax2.plot(ts, [p['P'] for p in series[:i + 1]], 'b--', label='Page (bits dehors)')
    ax2.set_xlim(0, 200)
    ax2.set_ylim(0, 1.05)
    ax2.legend(fontsize=7)
    ax2.grid(alpha=0.3)
    ax2.set_title('Mort et résurrection de l info')
    return []


FuncAnimation(fig, frame, frames=NF, interval=90).save(
    '/home/user/RATISS-QVM/demos/effet_horizon.gif', writer='pillow')
print('[effet] gif ok')

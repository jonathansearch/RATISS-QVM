"""Filtre Purcell : T1p x S, S = 1+(2.D/kf)^2 (Reed/Houck 2010).
T1 -> limite intrinseque, T2 x2.7. Figure demos/purcell_protection.png. MIT."""
import sys
sys.path.insert(0, '/home/user/RATISS-QVM')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from ratiss_qpu.microondes import CavityQED
from ratiss_qpu.coherence import evolve_open

D = '/home/user/RATISS-QVM/demos/'
sans = CavityQED()
avec = CavityQED(kappa_filt_hz=10e6)
print(f"[purcell] S={avec.suppression():.0f} T1 {sans.t1_s()*1e6:.1f}->{avec.t1_s()*1e6:.1f}us "
      f"T2 {sans.t2_s(0.01)*1e6:.1f}->{avec.t2_s(0.01)*1e6:.1f}us")

fig, ax = plt.subplots(1, 2, figsize=(11, 4))
kf = np.logspace(6, 8.5, 60)
ax[0].loglog(kf / 1e6, [CavityQED(kappa_filt_hz=k).t1_s() * 1e6 for k in kf], 'r-')
ax[0].axhline(300, color='k', ls='--', alpha=0.5)
ax[0].text(2, 320, 'limite intrinseque 300us')
ax[0].axvline(10, color='g', ls='--', alpha=0.5)
ax[0].text(12, 150, 'choix 10MHz')
ax[0].set_xlabel('bande filtre (MHz)'); ax[0].set_ylabel('T1 (us)')
ax[0].set_title('Protection Purcell : T1 vs bande')
rho0 = np.array([[0.5, 0.5], [0.5, 0.5]], dtype=complex)
H = np.zeros((2, 2), dtype=complex)
t = np.linspace(0, 800e-6, 200)
for c, lab, col in ((sans, 'sans filtre', 'r'), (avec, 'filtre 10MHz', 'g')):
    coh = [abs(evolve_open(rho0, H, ti, c, 0.01, steps=200)[0, 1]) for ti in t[::10]]
    ax[1].plot(t[::10] * 1e6, coh, col + 'o', ms=3, label=lab + ' (Lindblad)')
    ax[1].plot(t * 1e6, 0.5 * np.exp(-t / c.t2_s(0.01)), col + '-', alpha=0.5)
ax[1].set_xlabel('t (us)'); ax[1].set_ylabel('|rho01|')
ax[1].legend(); ax[1].set_title('Ramsey : T2 224 -> 600 us')
fig.suptitle('RATISS-QVM : filtre Purcell (S=160001, T1 -> 300us intrinseque)')
fig.tight_layout()
fig.savefig(D + 'purcell_protection.png', dpi=90)
print('[demo] png ok')

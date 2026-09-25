"""Décohérence micro-ondes réelle : T1/T2 dérivés du résonateur (Purcell+Gambetta),
vs NV phénoménologique. Figure demos/decoherence_microondes.png. MIT."""
import sys
sys.path.insert(0, '/home/user/RATISS-QVM')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from ratiss_qpu.microondes import CavityQED
from ratiss_qpu.coherence import DecoherenceModel

c = CavityQED()
print('[cQED]', {k: round(v, 3) if isinstance(v, float) else v
                 for k, v in c.specs().items()})
for T in (0.010, 0.050, 0.100):
    print(f'T={T*1000:.0f}mK : T1={c.t1_s(T)*1e6:.1f}us T2={c.t2_s(T)*1e6:.1f}us '
          f'({c.coherent_ops(T, 40e-9):.0f} portes @40ns)')

fig, ax = plt.subplots(1, 2, figsize=(11, 4))
Ts = np.logspace(np.log10(0.008), np.log10(0.25), 60)
ax[0].loglog(Ts * 1000, [c.t1_s(T) * 1e6 for T in Ts], 'r-', label='T1 (Purcell+int)')
ax[0].loglog(Ts * 1000, [c.t2_s(T) * 1e6 for T in Ts], 'b-', label='T2 (Gambetta)')
ax[0].axvline(10, color='k', ls='--', alpha=0.4)
ax[0].text(11, 200, 'frigo 10mK')
ax[0].set_xlabel('T frigo (mK)'); ax[0].set_ylabel('us'); ax[0].legend()
ax[0].set_title('cQED : T1/T2 vs temperature')
t = np.linspace(0, 400e-6, 300)
for T, col in ((0.010, 'b'), (0.050, 'g'), (0.100, 'r')):
    ax[1].plot(t * 1e6, 0.5 * np.exp(-t / c.t2_s(T)), col, label=f'cQED {T*1000:.0f}mK')
nv = DecoherenceModel()
ax[1].plot(t * 1e6, 0.5 * np.exp(-t / nv.t2_s(300.0)), 'k--', label='NV 300K (Jarmola)')
ax[1].set_xlabel('t (us)'); ax[1].set_ylabel('|rho01| (Ramsey)')
ax[1].legend(); ax[1].set_title('Decoherence : Ramsey |+>')
fig.suptitle('RATISS-QVM : decoherence micro-ondes reelle (Purcell + Gambetta)')
fig.tight_layout()
fig.savefig('/home/user/RATISS-QVM/demos/decoherence_microondes.png', dpi=90)
print('[demo] png ok')

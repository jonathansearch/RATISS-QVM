"""Fit S21 -> Q mesurés -> T1/T2 banc. Trace synthétique réaliste + figure.
Format CSV : f,I,Q (banc : export VNA). MIT."""
import sys
sys.path.insert(0, '/home/user/RATISS-QVM')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from ratiss_qpu.s21 import synth_trace, fit_s21, s21_hanger, save_csv
from ratiss_qpu.microondes import CavityQED

D = '/home/user/RATISS-QVM/demos/'
f, s, truth = synth_trace()
save_csv(D + 's21_synth.csv', f, s)
r = fit_s21(f, s)
print(f"{'param':6} {'vrai':>12} {'fit':>12}  err")
for k in ('fr', 'Ql', 'Qc', 'Qint', 'tau'):
    print('%-6s %12.5g %12.5g  %5.2f%%' % (k, truth[k], r[k],
          100 * abs(r[k] - truth[k]) / truth[k]))
c = CavityQED.from_s21(r)
print(f"[banc] T1={c.t1_s()*1e6:.1f}us T2={c.t2_s(0.01)*1e6:.1f}us (MESURES)")

m = s21_hanger(f, r['fr'], r['Ql'], r['Qc'], r['phi'], r['tau'], r['a'],
               r['alpha'])
fig, ax = plt.subplots(1, 2, figsize=(11, 4))
ax[0].plot((f - truth['fr']) / 1e6, 20 * np.log10(np.abs(s)), 'b.', ms=2,
           label='VNA (bruit)')
ax[0].plot((f - truth['fr']) / 1e6, 20 * np.log10(np.abs(m)), 'r-',
           label='fit hanger')
ax[0].set_xlabel('(f-fr) MHz'); ax[0].set_ylabel('|S21| dB'); ax[0].legend()
ax[0].set_title('Resonance : dip + fit')
ax[1].plot(s.real, s.imag, 'b.', ms=2, label='VNA')
ax[1].plot(m.real, m.imag, 'r-', label='fit')
ax[1].set_xlabel('I'); ax[1].set_ylabel('Q'); ax[1].legend(); ax[1].axis('equal')
ax[1].set_title('Plan complexe : cercle + fit')
fig.suptitle('RATISS-QVM : S21 -> Q_int=%.3g Q_ext=%.3g -> T1/T2 banc'
             % (r['Qint'], r['Qc']))
fig.tight_layout()
fig.savefig(D + 's21_fit.png', dpi=90)
print('[demo] png ok')

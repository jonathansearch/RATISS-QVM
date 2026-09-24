"""Ajuste p2q par jumeau : train λ={0.4,0.8,1.2,1.6}, TEST {0.6,1.0,1.4}.
Écrit p2q_fit + score test dans rqvm/data/twins.json. MIT."""
import json
import sys
sys.path.insert(0, '/home/user/RATISS-QVM')
from rqvm import pop, zz_contact, TwinBackend, load_twin_data

TRAIN = (0.4, 0.8, 1.2, 1.6)
TEST = (0.6, 1.0, 1.4)
GRID = (0.005, 0.01, 0.015, 0.02, 0.03, 0.04)

tw = load_twin_data()
for name in ('kingston', 'marrakesh'):
    real = {float(k): v['mean'] for k, v in tw[name]['zz_vs_lam'].items()}
    best, berr = None, 1e9
    for p2q in GRID:
        be = TwinBackend(name, p2q)
        err = sum(abs(zz_contact({k: int(v) for k, v in be.run(pop(l), shots=1500).result().get_counts().items()}) - real[l]) for l in TRAIN)
        print(f'{name} p2q={p2q}: train_err={err:.4f}', flush=True)
        if err < berr:
            best, berr = p2q, err
    be = TwinBackend(name, best)
    test = {l: round(zz_contact({k: int(v) for k, v in be.run(pop(l), shots=2000).result().get_counts().items()}), 4) for l in TEST}
    tw[name]['p2q_fit'] = best
    tw[name]['fit'] = {'train': list(TRAIN), 'train_err': round(berr, 4),
                       'test_pred': test,
                       'test_real': {l: round(real[l], 4) for l in TEST}}
    print(f'{name}: p2q={best} test_pred={test} test_real={tw[name]["fit"]["test_real"]}')
json.dump(tw, open('/home/user/RATISS-QVM/rqvm/data/twins.json', 'w'), indent=1)
print('[fit] ok')

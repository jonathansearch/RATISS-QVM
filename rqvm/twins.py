"""Jumeaux numériques Kingston/Marrakesh — calibrés sur NOS moissons IBM.
Données : rqvm/data/twins.json (cprops T1/T2/readout mesurés + courbes zz).
Hypothèses documentées : t_1q=60ns, t_2q=500ns ; readout symétrique (ro mesuré) ;
1 bouton global p2q ajusté sur λ train {0.4,0.8,1.2,1.6}, validé sur {0.6,1.0,1.4}.
MIT."""
from __future__ import annotations

import json
import os

DATA = os.path.join(os.path.dirname(__file__), 'data', 'twins.json')
T_1Q, T_2Q = 60e-9, 500e-9


def load_twin_data():
    return json.load(open(DATA))


def noise_model_for(name, p2q=None):
    """NoiseModel Aer depuis les cprops MESURÉES (+ p2q ajusté, tracé)."""
    from qiskit_aer.noise import (NoiseModel, ReadoutError,
                                  depolarizing_error, thermal_relaxation_error)
    tw = load_twin_data()[name]
    ch, cp = tw['chaine'], tw['cprops']
    nm = NoiseModel()
    for virt, phys in enumerate(ch):
        c = cp[str(phys)]
        t1, t2, ro = c['T1'] * 1e-6, c['T2'] * 1e-6, c['ro']
        t2 = min(t2, t1)  # snapshot: q31-K T2>T1 (impossible) -> clip, tracé
        nm.add_quantum_error(thermal_relaxation_error(t1, t2, T_1Q),
                             ['rz', 'sx', 'x', 'rx'], [virt])
        nm.add_readout_error(ReadoutError([[1 - ro, ro], [ro, 1 - ro]]), [virt])
    p2q = tw.get('p2q_fit', 0.02) if p2q is None else p2q
    nm.add_all_qubit_quantum_error(depolarizing_error(p2q, 2), ['cx', 'rzz'])
    return nm


class TwinBackend(__import__('qiskit').providers.BackendV2):
    """Un VRAI backend Qiskit : transpile + run, comme un QPU cloud."""

    def __init__(self, name='kingston', p2q=None):
        from qiskit.providers import BackendV2  # noqa
        tw = load_twin_data()[name]
        super().__init__(name=f'ratiss-twin-{name}',
                         description=f'Jumeau {name} (moisson {tw["job"]})',
                         backend_version='0.1.0')
        self.twin_name = name
        self.p2q = tw.get('p2q_fit', 0.02) if p2q is None else p2q
        self._nm = noise_model_for(name, self.p2q)
        self._target = self._build_target(tw)

    def _build_target(self, tw):
        from qiskit.transpiler import Target, InstructionProperties
        from qiskit.circuit import Measure
        from qiskit.circuit.library import IGate, RZGate, SXGate, XGate, CXGate, UGate, SwapGate
        from qiskit.circuit import Reset
        import numpy as np
        from qiskit.circuit import Parameter
        ch, cp = tw['chaine'], tw['cprops']
        tgt = Target(num_qubits=6, dt=4e-9)
        d1, drz, dm = {}, {}, {}
        for virt, phys in enumerate(ch):
            c = cp[str(phys)]
            e1 = 1 - np.exp(-T_1Q / (c['T1'] * 1e-6))
            d1[(virt,)] = InstructionProperties(error=e1, duration=T_1Q)
            drz[(virt,)] = InstructionProperties(error=0.0, duration=0.0)
            dm[(virt,)] = InstructionProperties(error=c['ro'], duration=1e-6)
        tgt.add_instruction(IGate(), d1)
        tgt.add_instruction(RZGate(Parameter('t')), drz)
        tgt.add_instruction(SXGate(), d1)
        tgt.add_instruction(XGate(), d1)
        tgt.add_instruction(Measure(), dm)
        tgt.add_instruction(UGate(Parameter('a'), Parameter('b'), Parameter('c')), d1)
        tgt.add_instruction(Reset(), {q: InstructionProperties(error=0.0, duration=1e-6)
                                      for q in dm})
        edges = ((0, 1), (1, 2), (2, 3), (3, 4), (4, 5))
        dsw = {e: InstructionProperties(error=0.03, duration=3 * T_2Q) for e in edges}
        tgt.add_instruction(SwapGate(), dsw)
        p2q = self.p2q
        dcx = {(a, b): InstructionProperties(error=p2q, duration=T_2Q)
               for a, b in ((0, 1), (1, 2), (2, 3), (3, 4), (4, 5))}
        tgt.add_instruction(CXGate(), dcx)
        return tgt

    @property
    def target(self):
        return self._target

    @property
    def max_circuits(self):
        return 1

    @classmethod
    def _default_options(cls):
        from qiskit.providers import Options
        return Options(shots=2000)

    def run(self, run_input, **kwargs):
        from qiskit import transpile
        from qiskit_aer import AerSimulator
        shots = kwargs.get('shots', 2000)
        tqc = transpile(run_input, self, seed_transpiler=kwargs.get('seed', 42))
        sim = AerSimulator(noise_model=self._nm, seed_simulator=kwargs.get('seed', 42))
        return sim.run(tqc, shots=shots)

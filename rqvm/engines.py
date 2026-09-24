"""Moteurs interchangeables — la symbiose.
Exact (numpy via StatevectorSampler) + Aer (bruit) + qsim (vitesse Google).
Tous exacts à 6q : même physique, moteurs différents. MIT."""
from __future__ import annotations


class ExactEngine:
    """Référence exacte (statevector)."""

    def run(self, circuit, shots=2000, seed=42):
        from qiskit.primitives import StatevectorSampler
        res = StatevectorSampler(seed=seed).run([circuit], shots=shots).result()
        return {k: int(v) for k, v in res[0].data.c.get_counts().items()}


class AerEngine:
    """Puissance Aer : bruit réaliste (NoiseModel optionnel)."""

    def __init__(self, noise_model=None):
        self.noise_model = noise_model

    def run(self, circuit, shots=2000, seed=42):
        from qiskit_aer import AerSimulator
        sim = AerSimulator(noise_model=self.noise_model, seed_simulator=seed)
        return {k: int(v) for k, v in
                sim.run(circuit, shots=shots).result().get_counts().items()}


class QsimEngine:
    """Fidélité/vitesse Google (qsim) — circuits Cirq natifs."""

    def run(self, circuit, shots=2000, seed=42):
        import numpy as np
        import qsimcirq
        res = qsimcirq.QSimSimulator().run(circuit, repetitions=shots)
        n = len(list(circuit.all_qubits()))
        out = {}
        for s in np.asarray(res.data.iloc[:, 0]).ravel():
            b = format(int(s), f'0{n}b')
            out[b] = out.get(b, 0) + 1
        return out


def run(circuit, shots=2000, engine='exact', noise_model=None, seed=42):
    """API unifiée. engine: exact | aer | qsim."""
    if engine == 'exact':
        return ExactEngine().run(circuit, shots, seed)
    if engine == 'aer':
        return AerEngine(noise_model).run(circuit, shots, seed)
    if engine == 'qsim':
        return QsimEngine().run(circuit, shots, seed)
    raise ValueError(f'moteur inconnu: {engine}')

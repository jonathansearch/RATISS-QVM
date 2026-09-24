"""Validation croisée RATISS ↔ IBM Quantum — la preuve à l'échelle atomique.

On fait tourner le MÊME état de Bell sur :
  1. notre simulateur exact (ratiss_qpu.two_qubit)
  2. un vrai QPU IBM supraconducteur (ibm_fez / marrakesh / kingston)

Si les distributions de mesure correspondent (à la fidélité hardware près),
notre chaîne logicielle est prouvée correcte face à du vrai hardware quantique.

HONNÊTETÉ SCIENTIFIQUE (charte RATISS) :
- IBM = supraconducteur à 15 mK. Cette validation prouve la JUSTESSE DE NOTRE
  ALGORITHME et de notre simulateur — PAS la cohérence de notre NV-diamant.
- La différence de fidélité entre IBM (bruit réel à 15 mK) et notre simulateur
  (idéal) est précisément ce que notre modèle de décohérence NV doit expliquer.

La clé IBM est lue depuis un fichier local sécurisé, JAMAIS affichée ni loggée.
"""

from __future__ import annotations

import numpy as np

from .two_qubit import bell_state, measure_probabilities, sample_2q


def build_bell_circuit():
    """Circuit Qiskit produisant |Φ+⟩ : H(0), CNOT(0→1), mesure."""
    from qiskit import QuantumCircuit
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure([0, 1], [0, 1])
    return qc


def run_on_simulator(shots: int = 4096, seed: int = 42) -> dict[str, int]:
    """Notre simulateur RATISS : distribution idéale (sans bruit hardware)."""
    rng = np.random.default_rng(seed)
    psi = bell_state()
    return sample_2q(psi, shots, rng)


def run_on_ibm(token_path: str, shots: int = 4096,
               backend_name: str | None = None) -> dict[str, int]:
    """Fait tourner le circuit de Bell sur un vrai QPU IBM."""
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
    from qiskit import transpile

    token = open(token_path).read().strip()
    service = QiskitRuntimeService(channel="ibm_quantum_platform", token=token)

    if backend_name:
        backend = service.backend(backend_name)
    else:
        backend = service.least_busy(operational=True, simulator=False)
    print(f"[IBM] backend choisi : {backend.name} ({backend.num_qubits} qubits)")

    qc = build_bell_circuit()
    tqc = transpile(qc, backend)
    sampler = Sampler(mode=backend)
    job = sampler.run([tqc], shots=shots)
    print(f"[IBM] job soumis : {job.job_id()} — attente du résultat...")
    result = job.result()

    pub = result[0]
    counts = pub.data.c.get_counts()
    return {k: int(v) for k, v in counts.items()}


def fidelity(counts_a: dict[str, int], counts_b: dict[str, int]) -> float:
    """Fidélité classique entre deux distributions (coeff. de Bhattacharyya²).
    1.0 = distributions identiques."""
    keys = {"00", "01", "10", "11"} | set(counts_a) | set(counts_b)
    na = sum(counts_a.get(k, 0) for k in keys) or 1
    nb = sum(counts_b.get(k, 0) for k in keys) or 1
    pa = {k: counts_a.get(k, 0) / na for k in keys}
    pb = {k: counts_b.get(k, 0) / nb for k in keys}
    bc = sum(np.sqrt(pa[k] * pb[k]) for k in keys)
    return float(bc ** 2)


def cross_validate(token_path: str | None = None, shots: int = 4096,
                   use_ibm: bool = True, backend_name: str | None = None) -> dict:
    """Preuve de concept complète. Retourne un rapport dict."""
    ideal = measure_probabilities(bell_state())
    sim_counts = run_on_simulator(shots)

    report = {
        "ideal_bell": ideal,
        "simulator_counts": sim_counts,
        "shots": shots,
    }

    if use_ibm and token_path:
        try:
            ibm_counts = run_on_ibm(token_path, shots, backend_name)
            report["ibm_backend_counts"] = ibm_counts
            report["fidelity_sim_vs_ibm"] = fidelity(sim_counts, ibm_counts)
            total = sum(ibm_counts.values())
            bell_pop = (ibm_counts.get("00", 0) + ibm_counts.get("11", 0)) / total
            report["ibm_bell_population"] = float(bell_pop)
        except Exception as e:
            report["ibm_error"] = f"{type(e).__name__}: {e}"

    return report

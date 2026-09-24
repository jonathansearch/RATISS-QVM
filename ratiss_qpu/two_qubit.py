"""Circuits à 2 qubits — intrication et états de Bell (validation IBM).

On étend le simulateur à 2 qubits pour produire l'état de Bell |Φ+⟩ =
(|00⟩ + |11⟩)/√2 — l'état intriqué fondamental. C'est LE test atomique : si
notre simulateur et le QPU IBM produisent la même distribution de mesure,
notre chaîne logicielle est validée sur du vrai hardware quantique.

Ordre des qubits : convention little-endian de Qiskit. État global = produit
tensoriel, qubit 0 = bit de poids faible. |q1 q0⟩.
"""

from __future__ import annotations

import numpy as np

from .qstate import H, I, X, Z

# Porte CNOT (contrôle = qubit 0, cible = qubit 1), convention Qiskit
# little-endian. Base d'état |q1 q0⟩ = {00, 01, 10, 11}. CNOT flippe q1 si q0=1 :
# |00⟩→|00⟩, |01⟩→|11⟩, |10⟩→|10⟩, |11⟩→|01⟩.
CNOT = np.array([
    [1, 0, 0, 0],
    [0, 0, 0, 1],
    [0, 0, 1, 0],
    [0, 1, 0, 0],
], dtype=complex)


def kron2(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Produit tensoriel de deux matrices (a ⊗ b)."""
    return np.kron(a, b)


def state_00() -> np.ndarray:
    """État |00⟩ = (1,0,0,0)."""
    return np.array([1.0, 0.0, 0.0, 0.0], dtype=complex)


def bell_state() -> np.ndarray:
    """Construit |Φ+⟩ = (|00⟩+|11⟩)/√2 = CNOT · (H⊗I) · |00⟩.

    H sur le qubit 0 (contrôle), puis CNOT (q0→q1). Résultat : amplitudes égales
    sur |00⟩ et |11⟩, nulles sur |01⟩ et |10⟩. Identique au circuit Qiskit :
    qc.h(0); qc.cx(0, 1)."""
    h_on_q0 = kron2(I, H)          # H sur q0 (poids faible), identité sur q1
    psi = h_on_q0 @ state_00()     # superposition sur q0 : (|00⟩+|01⟩)/√2
    psi = CNOT @ psi               # intrication : (|00⟩+|11⟩)/√2
    return psi


def measure_probabilities(state: np.ndarray) -> dict[str, float]:
    """Distribution de Born sur les 4 états de base {|00⟩,|01⟩,|10⟩,|11⟩}.
    Clés = bitstring 'q1q0'."""
    probs = np.abs(state) ** 2
    labels = ["00", "01", "10", "11"]
    return {labels[i]: float(probs[i]) for i in range(4)}


def sample_2q(state: np.ndarray, shots: int, rng: np.random.Generator) -> dict[str, int]:
    """Échantillonne `shots` mesures selon la distribution de Born exacte."""
    probs = np.abs(state) ** 2
    probs = probs / probs.sum()    # renormalisation garde-fou
    labels = ["00", "01", "10", "11"]
    idx = rng.choice(4, size=shots, p=probs)
    counts = {labels[i]: int(np.sum(idx == i)) for i in range(4)}
    return counts


def concurrence_pure(state: np.ndarray) -> float:
    """Concurrence d'un état pur à 2 qubits : C = |<ψ|σy⊗σy|ψ*⟩|.
    C=1 pour un état de Bell (maximalement intriqué), 0 pour un état produit.
    C'est LA mesure d'intrication — la preuve qu'on a de la vraie corrélation
    quantique, pas classique."""
    yy = kron2(np.array([[0, -1j], [1j, 0]]), np.array([[0, -1j], [1j, 0]]))
    return float(abs(np.vdot(state, yy @ state.conj())))

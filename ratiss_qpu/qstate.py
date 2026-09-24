"""Simulateur d'état quantique exact — noyau de RATISS-QPU-AMBIENT.

Propagation d'état vectoriel pur + matrice densité, portes unitaires exactes,
mesure projective. Aucun raccourci : c'est de l'algèbre linéaire exacte (numpy),
pas un simulateur approché. La décohérence est traitée dans coherence.py via
l'équation maîtresse de Lindblad (matrices densité obligatoires pour le bruit).

Conventions :
- Qubit = vecteur colonne de C^2, base {|0⟩=(1,0), |1⟩=(0,1)}.
- Hamiltonien en unités angulaires (rad/s) : H a les dimensions d'une fréquence
  angulaire ; l'évolution est U = exp(-i H t). On pose ħ = 1.
- Pour le NV : sous-espace {ms=0, ms=-1}, couplé par micro-onde (Rabi).

Unités SI dans les paramètres physiques (tesla, kelvin, seconde, hertz).
"""

from __future__ import annotations

import numpy as np

# --- Portes standard (matrices de Pauli et dérivées), exactes ---
I = np.eye(2, dtype=complex)
X = np.array([[0, 1], [1, 0]], dtype=complex)
Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
Z = np.array([[1, 0], [0, -1]], dtype=complex)
H = (X + Z) / np.sqrt(2.0)                      # Hadamard
S = np.diag([1.0, 1j])                          # porte de phase

# Projecteurs de mesure dans la base Z
P0 = np.array([[1, 0], [0, 0]], dtype=complex)  # |0><0|
P1 = np.array([[0, 0], [0, 1]], dtype=complex)  # |1><1|


def ket0() -> np.ndarray:
    return np.array([1.0, 0.0], dtype=complex)


def ket1() -> np.ndarray:
    return np.array([0.0, 1.0], dtype=complex)


def bloch_state(theta: float, phi: float) -> np.ndarray:
    """État pur sur la sphère de Bloch : cos(θ/2)|0⟩ + e^{iφ} sin(θ/2)|1⟩."""
    return np.array([np.cos(theta / 2.0),
                     np.exp(1j * phi) * np.sin(theta / 2.0)], dtype=complex)


def is_normalized(state: np.ndarray, tol: float = 1e-9) -> bool:
    return abs(np.vdot(state, state).real - 1.0) < tol


def apply_gate(state: np.ndarray, gate: np.ndarray) -> np.ndarray:
    """Applique une porte unitaire à un état pur. Vérifie l'unitarité."""
    if gate.shape != (2, 2):
        raise ValueError("porte 1-qubit attendue (2×2)")
    # Unitarité : U†U = I
    if not np.allclose(gate.conj().T @ gate, I, atol=1e-9):
        raise ValueError("porte non unitaire")
    return gate @ state


def measure_z(state: np.ndarray, rng: np.random.Generator) -> tuple[int, np.ndarray]:
    """Mesure projective en base Z. Retourne (résultat 0/1, état post-mesure).
    Probabilités de Born exactes : p0 = |<0|ψ>|²."""
    p0 = float(abs(state[0]) ** 2)
    p0 = min(max(p0, 0.0), 1.0)  # garde-fou numérique
    outcome = 0 if rng.random() < p0 else 1
    collapsed = ket0() if outcome == 0 else ket1()
    return outcome, collapsed


def bloch_vector(state_or_rho: np.ndarray) -> np.ndarray:
    """Vecteur de Bloch (x, y, z) d'un état pur ou d'une matrice densité.
    r_i = Tr(ρ σ_i). Pour un état pur |ψ⟩ : ρ = |ψ><ψ|."""
    if state_or_rho.ndim == 1:
        rho = np.outer(state_or_rho, state_or_rho.conj())
    else:
        rho = state_or_rho
    x = np.trace(rho @ X).real
    y = np.trace(rho @ Y).real
    z = np.trace(rho @ Z).real
    return np.array([x, y, z], dtype=float)


def purity(rho: np.ndarray) -> float:
    """Pureté Tr(ρ²) : 1 = état pur, 1/2 = état maximalement mixte (1 qubit).
    C'est la mesure directe de la cohérence restante."""
    return float(np.trace(rho @ rho).real)

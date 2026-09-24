"""Hamiltonien du centre NV et dynamique micro-onde — physique exacte.

Le centre NV− est un triplet de spin S=1. On se restreint au sous-espace qubit
{ms=0, ms=-1}. Le Hamiltonien de l'état fondamental (unités angulaires, ħ=1) :

    H = D·Sz² + γ_e·B·Sz + Ω(t)·Sx·cos(ω_mw·t)

où :
- D = 2.87 GHz (splitting à champ nul entre ms=0 et ms=±1) — le zéro-field splitting.
- γ_e = 28.0 GHz/T (gyromagnétique électronique).
- B = champ magnétique statique appliqué (lève la dégénérescence ms=±1, effet Zeeman).
- Ω(t) = pulsation de Rabi micro-onde (contrôle de la porte).
- Sx, Sz = matrices de spin-1 restreintes au sous-espace 2D.

Sous approximation d'onde tournante (RWA) et à résonance (ω_mw = D − γ_e B),
le Hamiltonien dans le référentiel tournant devient H_rot = (Ω/2)·Sx → rotations
de Rabi : un pulse de durée t effectue une rotation d'angle Ω·t.

Références : Doherty et al., Physics Reports 528:1 (2013) — "The nitrogen-vacancy
colour centre in diamond" ; Rondin et al., Rep. Prog. Phys. 77 (2014).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.linalg import expm

from .qstate import X, Z, apply_gate

# --- Constantes physiques du NV− (sourcées, PHYSICS.md) ---
D_ZERO_FIELD_HZ = 2.87e9          # splitting à champ nul (Hz)
GAMMA_E_HZ_PER_T = 28.0e9         # gyromagnétique électronique (Hz/T)
HBAR = 1.0                        # unités angulaires (ħ = 1)


@dataclass
class NVCenter:
    """Un centre NV piloté par micro-onde. qubit = sous-espace {ms=0, ms=-1}.

    b_tesla    : champ statique Zeeman (lève la dégénérescence ms=±1)
    rabi_hz    : pulsation de Rabi du champ micro-onde (contrôle de porte)
    """
    b_tesla: float = 0.05         # ~500 G, champ de travail typique
    rabi_hz: float = 1.0e6        # 1 MHz → porte π en 0.5 µs

    @property
    def transition_hz(self) -> float:
        """Fréquence de transition ms=0 ↔ ms=-1 = D − γ_e·B (effet Zeeman)."""
        return D_ZERO_FIELD_HZ - GAMMA_E_HZ_PER_T * self.b_tesla

    def rabi_frequency_hz(self) -> float:
        return self.rabi_hz

    def gate_time_s(self, angle: float) -> float:
        """Durée d'une rotation d'`angle` (rad) à la pulsation de Rabi Ω."""
        return float(abs(angle) / (2.0 * np.pi * self.rabi_hz))

    def rotation(self, angle: float, phase: float = 0.0) -> np.ndarray:
        """Porte = rotation de Rabi d'`angle` autour de l'axe (cos φ, sin φ, 0)
        dans le plan équatorial. U = exp(-i (angle/2)(cosφ X + sinφ Y))."""
        ax = np.cos(phase) * X + np.sin(phase) * np.array([[0, -1j], [1j, 0]])
        return expm(-0.5j * angle * ax)

    def pi_pulse(self) -> np.ndarray:
        """Impulsion π : |0⟩ ↔ |1⟩ (rotation de 180°)."""
        return self.rotation(np.pi)

    def pi_half_pulse(self) -> np.ndarray:
        """Impulsion π/2 : superposition équatoriale (Hadamard-like)."""
        return self.rotation(np.pi / 2.0)

    def rabi_evolution(self, state: np.ndarray, t_s: float) -> np.ndarray:
        """Évolution libre sous micro-onde à résonance pendant t_s.
        Angle de Rabi = 2π·Ω·t. Exact (RWA, résonance)."""
        angle = 2.0 * np.pi * self.rabi_hz * t_s
        return apply_gate(state, self.rotation(angle))

"""Décohérence micro-ondes RÉELLE — qubit supraconducteur + résonateur (cQED).

Au lieu du modèle phénoménologique (Jarmola), T1/T2 sont DÉRIVÉS des paramètres
micro-ondes mesurables sur le banc : fréquences, couplage g, facteurs Q, T frigo.
Références : Blais et al. RMP 2021 (cQED), Gambetta et al. PRA 2006 (déphasage
thermique), Bosch-Hale... non — Purcell 1946 (relaxation). SOURCÉ, SI. MIT.

Modèle dispersif (|Δ| >> g) :
- κ/2π = f_r / Q_l,  Q_l^-1 = Q_int^-1 + Q_ext^-1   (largeur résonateur)
- χ = g²/Δ                                          (shift dispersif, rad/s)
- γ_Purcell = κ (g/Δ)²                              (T1 limite Purcell)
- filtre : T1p -> T1p x S, S = 1+(2.D_qf/k_f)²   (Reed/Houck 2010)
- 1/T1 = 1/T1_Purcell + 1/T1_int                    (T1_int = diélectrique/qp)
- n_th(f,T) = 1/(exp(hf/kT) - 1)                    (photons thermiques)
- Γ_φ = (κ/2) Re[ sqrt((1+2iχ/κ)² + 8i n_th χ/κ) - 1 ]  (Gambetta exact)
- 1/T2 = 1/(2T1) + Γ_φ

API compatible DecoherenceModel (t1_s/t2_s/coherent_ops) : se branche DIRECT
dans evolve_open/bloct_trajectory de coherence.py. Défauts = transmon IBM-like.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

H_SI = 6.62607015e-34      # J.s
K_B = 1.380649e-23         # J/K


def n_th(f_hz: float, t_kelvin: float) -> float:
    """Photons thermiques de Bose à (f, T). Garde overflow -> 0."""
    if t_kelvin <= 0:
        return 0.0
    x = H_SI * f_hz / (K_B * t_kelvin)
    if x > 700:
        return 0.0
    return float(1.0 / (np.exp(x) - 1.0))


def gamma_phi_gambetta(kappa: float, chi: float, nth: float) -> float:
    """Déphasage photon-shot-noise, formule EXACTE de Gambetta et al. (2006).
    kappa, chi en rad/s. -> taux en s^-1 (>= 0)."""
    if nth <= 0 or chi == 0:
        return 0.0
    z = (1 + 2j * chi / kappa) ** 2 + 8j * nth * chi / kappa
    return float(max((kappa / 2) * np.sqrt(z + 0j).real - 0.0 - (kappa / 2) * 1.0, 0.0))


@dataclass
class CavityQED:
    """Qubit transmon + résonateur lecture. Défauts IBM-like (bravo les Q)."""
    f_q_hz: float = 5.0e9      # qubit
    f_r_hz: float = 7.0e9      # résonateur
    g_hz: float = 100.0e6      # couplage transverse
    q_int: float = 1.0e6       # Q interne résonateur
    q_ext: float = 2.0e4       # Q couplage (lecture)
    t_fridge_k: float = 0.010  # 10 mK
    t1_int_s: float = 300.0e-6  # T1 intrinsèque (diélectrique, qp)
    f_filt_hz: float = 7.0e9   # filtre Purcell (passe-bande, sur résonateur)
    kappa_filt_hz: float = 0.0  # bande passante (Hz, cyclique) ; 0 = pas de filtre

    def q_loaded(self) -> float:
        return float(1.0 / (1.0 / self.q_int + 1.0 / self.q_ext))

    def kappa(self) -> float:
        """κ en rad/s."""
        return float(2 * np.pi * self.f_r_hz / self.q_loaded())

    def delta(self) -> float:
        return float(2 * np.pi * (self.f_q_hz - self.f_r_hz))

    def chi(self) -> float:
        """Shift dispersif χ = g²/Δ (rad/s). Valide si |Δ| >> g."""
        return float((2 * np.pi * self.g_hz) ** 2 / self.delta())

    def suppression(self) -> float:
        """Facteur S du filtre Purcell (Reed/Houck 2010) : le filtre passe
        f_r mais réfléchit f_q -> S = 1 + (2.D_qf/k_f)^2. 1.0 sans filtre."""
        if self.kappa_filt_hz <= 0:
            return 1.0
        d = 2 * (self.f_q_hz - self.f_filt_hz) / self.kappa_filt_hz
        return float(1.0 + d ** 2)

    def t1_purcell_s(self) -> float:
        g = 2 * np.pi * self.g_hz
        t1p = 1.0 / (self.kappa() * (g / self.delta()) ** 2)
        return float(t1p * self.suppression())

    def gamma_phi(self, t_kelvin: float) -> float:
        nth = n_th(self.f_r_hz, t_kelvin)
        return gamma_phi_gambetta(self.kappa(), self.chi(), nth)

    # --- API DecoherenceModel (plug-in direct dans evolve_open) ---
    def t1_s(self, t_kelvin: float = 0.010) -> float:
        t1p = self.t1_purcell_s()
        return float(1.0 / (1.0 / t1p + 1.0 / self.t1_int_s))

    def t2_s(self, t_kelvin: float = 0.010) -> float:
        t1 = self.t1_s(t_kelvin)
        gphi = self.gamma_phi(t_kelvin)
        return float(1.0 / (1.0 / (2 * t1) + gphi))

    def coherent_ops(self, t_kelvin: float, gate_time_s: float) -> float:
        return float(self.t2_s(t_kelvin) / gate_time_s)

    @classmethod
    def from_s21(cls, fit: dict, f_q_hz: float = 5.0e9,
                 g_hz: float = 100.0e6, t_fridge_k: float = 0.010,
                 t1_int_s: float = 300.0e-6) -> 'CavityQED':
        """Construit depuis fit_s21() : f_r, Q_int, Q_ext MESURÉS -> T1/T2 banc."""
        return cls(f_q_hz=f_q_hz, f_r_hz=float(fit['fr']),
                   g_hz=g_hz, q_int=float(fit['Qint']),
                   q_ext=float(fit['Qc']), t_fridge_k=t_fridge_k,
                   t1_int_s=t1_int_s)

    def specs(self) -> dict:
        t1, t2 = self.t1_s(self.t_fridge_k), self.t2_s(self.t_fridge_k)
        return {'f_q_GHz': self.f_q_hz / 1e9, 'f_r_GHz': self.f_r_hz / 1e9,
                'g_MHz': self.g_hz / 1e6, 'Q_loaded': round(self.q_loaded()),
                'kappa_kHz': self.kappa() / 2 / np.pi / 1e3,
                'chi_MHz': self.chi() / 2 / np.pi / 1e6,
                'T1_Purcell_us': self.t1_purcell_s() * 1e6,
                'T1_us': t1 * 1e6, 'T2_us': t2 * 1e6,
                'n_th': n_th(self.f_r_hz, self.t_fridge_k),
                'S_filtre': self.suppression()}

"""Banc NV virtuel — valide la chaîne de mesure AVANT l'achat de matériel.

Produit des données expérimentales réalistes (comptages de photons bruités) à
partir de la physique du NV, pour les 4 séquences de mesure. C'est le "hardware
virtuel" : le logiciel d'analyse est développé et testé ici, puis branché
tel quel sur l'APD réel.

Modèle de fluorescence (physique du NV) :
- ms=0 fluoresce fort (état "brillant"), ms=±1 ~30 % moins (état "sombre").
- Le comptage de photons suit une loi de Poisson (bruit de grenaille quantique).
- Contraste ODMR typique : ~10-30 % de chute de fluorescence à la résonance.

C'est la transdisciplinarité : optique (fluorescence) × quantique (spin) ×
statistique (comptage de Poisson). Le bruit n'est PAS un défaut du code — c'est
la réalité physique de la détection de photons uniques.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ratiss_qpu.nv_center import NVCenter, D_ZERO_FIELD_HZ, GAMMA_E_HZ_PER_T


@dataclass
class VirtualBench:
    """Simule le banc optique + NV avec bruit de photon réaliste.

    nv               : le centre NV (champ B, Rabi Ω)
    fluorescence_ms0 : taux de comptage de l'état brillant (photons/s)
    contrast         : contraste ODMR (fraction de chute à la résonance)
    read_time_s      : durée de la fenêtre de comptage
    repetitions      : nb de répétitions par point de mesure (la pratique réelle
                       d'un banc NV : on moyenne pour battre le bruit de grenaille)
    """
    nv: NVCenter = None
    fluorescence_ms0: float = 1.0e6     # 1 Mcounts/s (APD typique sur NV)
    contrast: float = 0.20              # 20 % de contraste ODMR
    read_time_s: float = 0.3e-6         # 300 ns de lecture
    repetitions: int = 2000             # moyennage (bat le bruit de Poisson)
    seed: int | None = None

    def __post_init__(self):
        if self.nv is None:
            self.nv = NVCenter()
        self.rng = np.random.default_rng(self.seed)

    def resonance_hz(self) -> float:
        """Fréquence de résonance ODMR = transition Zeeman du NV."""
        return self.nv.transition_hz

    def _count_photons(self, brightness: float) -> int:
        """Comptage de Poisson : nombre de photons sur la fenêtre de lecture.
        brightness ∈ [0,1] : 1 = ms=0 (brillant), 1-contrast = ms=±1."""
        mean = (self.fluorescence_ms0 * brightness * self.read_time_s
                * self.repetitions)
        return int(self.rng.poisson(max(mean, 0.0)))

    def odmr_point(self, mw_frequency_hz: float, linewidth_hz: float = 3.0e6) -> int:
        """Un point de spectre ODMR : fluorescence vs fréquence micro-onde.

        À la résonance (profil lorentzien), le spin est transféré vers ms=±1 →
        la fluorescence chute. linewidth = largeur de raie (~MHz)."""
        detuning = mw_frequency_hz - self.resonance_hz()
        lorentz = linewidth_hz ** 2 / (detuning ** 2 + linewidth_hz ** 2)
        brightness = 1.0 - self.contrast * lorentz
        return self._count_photons(brightness)

    def rabi_point(self, tau_s: float) -> int:
        """Un point d'oscillation de Rabi : fluorescence vs durée du pulse µ-onde.
        La population ms=0 oscille en cos²(π·Ω·τ)."""
        angle = 2.0 * np.pi * self.nv.rabi_hz * tau_s
        p_ms0 = np.cos(angle / 2.0) ** 2        # probabilité de rester en ms=0
        brightness = p_ms0 * 1.0 + (1 - p_ms0) * (1 - self.contrast)
        return self._count_photons(brightness)

    def ramsey_point(self, tau_s: float, t2star_s: float,
                     detuning_hz: float = 1.0e6) -> int:
        """Un point de franges de Ramsey : décroissance de la cohérence libre.
        Signal ∝ ½[1 + cos(2π·Δ·τ)·exp(−(τ/T2*)²)]  (décroissance gaussienne)."""
        envelope = np.exp(-((tau_s / t2star_s) ** 2))
        fringe = np.cos(2.0 * np.pi * detuning_hz * tau_s)
        coherence = 0.5 * (1.0 + fringe * envelope)
        brightness = coherence * 1.0 + (1 - coherence) * (1 - self.contrast)
        return self._count_photons(brightness)

    def hahn_echo_point(self, tau_s: float, t2_s: float) -> int:
        """Un point d'écho de Hahn : décroissance exponentielle de la cohérence.
        Signal ∝ ½[1 + exp(−2τ/T2)] — le pulse π refocalise le déphasing statique."""
        coherence = 0.5 * (1.0 + np.exp(-2.0 * tau_s / t2_s))
        brightness = coherence * 1.0 + (1 - coherence) * (1 - self.contrast)
        return self._count_photons(brightness)

    # --- Balayages complets (comme le vrai banc) ---

    def sweep_odmr(self, f_start_hz: float, f_stop_hz: float,
                   n_points: int, linewidth_hz: float = 3.0e6) -> tuple[np.ndarray, np.ndarray]:
        freqs = np.linspace(f_start_hz, f_stop_hz, n_points)
        counts = np.array([self.odmr_point(f, linewidth_hz) for f in freqs])
        return freqs, counts

    def sweep_rabi(self, tau_max_s: float, n_points: int) -> tuple[np.ndarray, np.ndarray]:
        taus = np.linspace(0.0, tau_max_s, n_points)
        counts = np.array([self.rabi_point(t) for t in taus])
        return taus, counts

    def sweep_ramsey(self, tau_max_s: float, n_points: int,
                     t2star_s: float, detuning_hz: float = 1.0e6):
        taus = np.linspace(0.0, tau_max_s, n_points)
        counts = np.array([self.ramsey_point(t, t2star_s, detuning_hz) for t in taus])
        return taus, counts

    def sweep_hahn(self, tau_max_s: float, n_points: int, t2_s: float):
        taus = np.linspace(0.0, tau_max_s, n_points)
        counts = np.array([self.hahn_echo_point(t, t2_s) for t in taus])
        return taus, counts
